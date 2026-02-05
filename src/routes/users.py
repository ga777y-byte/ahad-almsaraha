from flask import Blueprint, jsonify, request, current_app
from src.models.user import User, UserProfile, db
from src.routes.auth import token_required
from datetime import datetime

users_bp = Blueprint('users', __name__)

def admin_required(f):
    """ديكوريتر للتحقق من صلاحيات المدير"""
    def admin_decorated(current_user, *args, **kwargs):
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لإدارة المستخدمين'}), 403
        return f(current_user, *args, **kwargs)
    admin_decorated.__name__ = f.__name__ + '_admin'
    return admin_decorated

@users_bp.route('/users', methods=['GET'])
@token_required
def get_all_users(current_user):
    """الحصول على جميع المستخدمين"""
    try:
        # التحقق من الصلاحيات
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لعرض المستخدمين'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        role = request.args.get('role', '')
        department = request.args.get('department', '')
        is_active = request.args.get('is_active', '')
        
        # بناء الاستعلام
        query = User.query
        
        # البحث
        if search:
            query = query.filter(
                (User.name.contains(search)) |
                (User.email.contains(search)) |
                (User.department.contains(search))
            )
        
        # تصفية حسب الدور
        if role:
            query = query.filter(User.role == role)
        
        # تصفية حسب القسم
        if department:
            query = query.filter(User.department == department)
        
        # تصفية حسب الحالة
        if is_active:
            active_status = is_active.lower() == 'true'
            query = query.filter(User.is_active == active_status)
        
        # ترتيب النتائج
        query = query.order_by(User.created_at.desc())
        
        # تطبيق التصفح
        users = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'page': page,
                'pages': users.pages,
                'per_page': per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get all users error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب المستخدمين'}), 500

@users_bp.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    """الحصول على مستخدم معين"""
    try:
        # التحقق من الصلاحيات (المدير أو المستخدم نفسه)
        if not current_user.can_manage_users() and current_user.id != user_id:
            return jsonify({'message': 'ليس لديك صلاحية لعرض هذا المستخدم'}), 403
        
        user = User.query.get_or_404(user_id)
        
        return jsonify({
            'user': user.to_dict(),
            'profile': user.profile.to_dict() if user.profile else None
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get user error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب المستخدم'}), 500

@users_bp.route('/users', methods=['POST'])
@token_required
@admin_required
def create_user(current_user):
    """إنشاء مستخدم جديد (للمدير فقط)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'البيانات مطلوبة'}), 400
        
        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        role = data.get('role', 'user')
        department = data.get('department', '').strip()
        phone = data.get('phone', '').strip()
        send_invitation = data.get('send_invitation', True)
        
        # التحقق من البيانات المطلوبة
        if not email or not name:
            return jsonify({'message': 'البريد الإلكتروني والاسم مطلوبان'}), 400
        
        # التحقق من عدم وجود المستخدم مسبقاً
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'message': 'البريد الإلكتروني مستخدم مسبقاً'}), 409
        
        # إنشاء المستخدم الجديد
        new_user = User(
            email=email,
            name=name,
            role=role,
            department=department,
            phone=phone,
            is_active=True,
            is_verified=False  # سيتم التحقق عند أول تسجيل دخول
        )
        
        # تعيين كلمة مرور مؤقتة
        temp_password = data.get('temp_password', 'temp123456')
        new_user.set_password(temp_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # إنشاء الملف الشخصي
        profile = UserProfile(user_id=new_user.id)
        db.session.add(profile)
        db.session.commit()
        
        # إرسال دعوة إذا كان مطلوب
        if send_invitation:
            # هنا يمكن إرسال بريد إلكتروني للمستخدم الجديد
            pass
        
        return jsonify({
            'message': 'تم إنشاء المستخدم بنجاح',
            'user': new_user.to_dict(),
            'temp_password': temp_password if not send_invitation else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create user error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء المستخدم'}), 500

@users_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    """تحديث مستخدم"""
    try:
        # التحقق من الصلاحيات
        if not current_user.can_manage_users() and current_user.id != user_id:
            return jsonify({'message': 'ليس لديك صلاحية لتحديث هذا المستخدم'}), 403
        
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'البيانات مطلوبة'}), 400
        
        # تحديث البيانات الأساسية
        if 'name' in data and data['name'].strip():
            user.name = data['name'].strip()
        
        if 'department' in data:
            user.department = data['department'].strip()
        
        if 'phone' in data:
            user.phone = data['phone'].strip()
        
        # تحديث الدور (للمدير فقط)
        if 'role' in data and current_user.can_manage_users():
            user.role = data['role']
        
        # تحديث الحالة (للمدير فقط)
        if 'is_active' in data and current_user.can_manage_users():
            user.is_active = data['is_active']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث المستخدم بنجاح',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update user error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تحديث المستخدم'}), 500

@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    """حذف مستخدم (للمدير فقط)"""
    try:
        if current_user.id == user_id:
            return jsonify({'message': 'لا يمكنك حذف حسابك الخاص'}), 400
        
        user = User.query.get_or_404(user_id)
        
        # حذف الملف الشخصي أولاً
        if user.profile:
            db.session.delete(user.profile)
        
        # حذف المستخدم
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'تم حذف المستخدم بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete user error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في حذف المستخدم'}), 500

@users_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@token_required
@admin_required
def activate_user(current_user, user_id):
    """تفعيل مستخدم"""
    try:
        user = User.query.get_or_404(user_id)
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم تفعيل المستخدم بنجاح',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Activate user error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تفعيل المستخدم'}), 500

@users_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@token_required
@admin_required
def deactivate_user(current_user, user_id):
    """إلغاء تفعيل مستخدم"""
    try:
        if current_user.id == user_id:
            return jsonify({'message': 'لا يمكنك إلغاء تفعيل حسابك الخاص'}), 400
        
        user = User.query.get_or_404(user_id)
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم إلغاء تفعيل المستخدم بنجاح',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Deactivate user error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إلغاء تفعيل المستخدم'}), 500

@users_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@token_required
@admin_required
def admin_reset_password(current_user, user_id):
    """إعادة تعيين كلمة مرور المستخدم (للمدير فقط)"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        new_password = data.get('new_password', 'temp123456')
        
        # تعيين كلمة المرور الجديدة
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم إعادة تعيين كلمة المرور بنجاح',
            'temp_password': new_password
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Admin reset password error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إعادة تعيين كلمة المرور'}), 500

@users_bp.route('/users/roles', methods=['GET'])
@token_required
def get_user_roles(current_user):
    """الحصول على قائمة الأدوار المتاحة"""
    try:
        roles = [
            {'value': 'user', 'label': 'مستخدم'},
            {'value': 'technician', 'label': 'فني صيانة'},
            {'value': 'safety_manager', 'label': 'مسؤول سلامة'},
            {'value': 'admin', 'label': 'مدير'},
            {'value': 'super_admin', 'label': 'مدير عام'}
        ]
        
        return jsonify({'roles': roles}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get user roles error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الأدوار'}), 500

@users_bp.route('/users/departments', methods=['GET'])
@token_required
def get_departments(current_user):
    """الحصول على قائمة الأقسام"""
    try:
        # الحصول على الأقسام من قاعدة البيانات
        departments_query = db.session.query(User.department).filter(
            User.department.isnot(None),
            User.department != ''
        ).distinct().all()
        
        departments = [dept[0] for dept in departments_query if dept[0]]
        
        # إضافة أقسام افتراضية إذا لم تكن موجودة
        default_departments = [
            'إدارة السلامة',
            'الصيانة',
            'الطوارئ',
            'الإدارة العامة',
            'التمريض',
            'الأطباء',
            'الأمن'
        ]
        
        for dept in default_departments:
            if dept not in departments:
                departments.append(dept)
        
        return jsonify({'departments': sorted(departments)}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get departments error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الأقسام'}), 500

@users_bp.route('/users/stats', methods=['GET'])
@token_required
def get_users_stats(current_user):
    """الحصول على إحصائيات المستخدمين"""
    try:
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لعرض الإحصائيات'}), 403
        
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        verified_users = User.query.filter_by(is_verified=True).count()
        
        # إحصائيات الأدوار
        roles_stats = db.session.query(
            User.role,
            db.func.count(User.id).label('count')
        ).group_by(User.role).all()
        
        # إحصائيات الأقسام
        departments_stats = db.session.query(
            User.department,
            db.func.count(User.id).label('count')
        ).filter(
            User.department.isnot(None),
            User.department != ''
        ).group_by(User.department).all()
        
        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'inactive_users': total_users - active_users,
            'unverified_users': total_users - verified_users,
            'roles_distribution': [
                {'role': role, 'count': count} for role, count in roles_stats
            ],
            'departments_distribution': [
                {'department': dept, 'count': count} for dept, count in departments_stats
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get users stats error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الإحصائيات'}), 500

