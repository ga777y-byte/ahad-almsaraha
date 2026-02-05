from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash
from src.models.user import User, UserSession, UserProfile, db
from datetime import datetime, timedelta
import secrets
import re
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """التحقق من صحة البريد الإلكتروني"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """التحقق من قوة كلمة المرور"""
    if len(password) < 6:
        return False, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
    return True, "كلمة مرور صالحة"

def token_required(f):
    """ديكوريتر للتحقق من الرمز المميز"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # البحث عن الرمز في الهيدر
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer TOKEN
            except IndexError:
                return jsonify({'message': 'رمز مصادقة غير صالح'}), 401
        
        if not token:
            return jsonify({'message': 'رمز المصادقة مطلوب'}), 401
        
        try:
            current_user = User.verify_token(token)
            if not current_user:
                return jsonify({'message': 'رمز مصادقة منتهي الصلاحية أو غير صالح'}), 401
        except Exception as e:
            return jsonify({'message': 'خطأ في التحقق من الرمز المميز'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@auth_bp.route('/login', methods=['POST'])
def login():
    """تسجيل الدخول"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'البيانات مطلوبة'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember_me = data.get('rememberMe', False)
        
        # التحقق من وجود البيانات المطلوبة
        if not email or not password:
            return jsonify({'message': 'البريد الإلكتروني وكلمة المرور مطلوبان'}), 400
        
        # التحقق من صحة البريد الإلكتروني
        if not validate_email(email):
            return jsonify({'message': 'البريد الإلكتروني غير صالح'}), 400
        
        # البحث عن المستخدم
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'message': 'البريد الإلكتروني أو كلمة المرور غير صحيحة'}), 401
        
        # التحقق من حالة المستخدم
        if not user.is_active:
            return jsonify({'message': 'الحساب غير مفعل. يرجى التواصل مع المدير'}), 403
        
        # تحديث وقت آخر تسجيل دخول
        user.update_last_login()
        
        # إنشاء الرمز المميز
        token_expires = 30 * 24 * 3600 if remember_me else 24 * 3600  # 30 يوم أو 24 ساعة
        token = user.generate_token(expires_in=token_expires)
        
        # إنشاء جلسة إذا كان المستخدم يريد التذكر
        if remember_me:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(days=30)
            
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                expires_at=expires_at
            )
            db.session.add(user_session)
            db.session.commit()
        
        # إعداد بيانات الاستجابة
        response_data = {
            'message': 'تم تسجيل الدخول بنجاح',
            'token': token,
            'user': user.to_dict(),
            'expires_in': token_expires
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تسجيل الدخول'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """تسجيل مستخدم جديد"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'البيانات مطلوبة'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        role = data.get('role', 'user')
        department = data.get('department', '').strip()
        phone = data.get('phone', '').strip()
        
        # التحقق من البيانات المطلوبة
        if not email or not password or not name:
            return jsonify({'message': 'البريد الإلكتروني وكلمة المرور والاسم مطلوبة'}), 400
        
        # التحقق من صحة البريد الإلكتروني
        if not validate_email(email):
            return jsonify({'message': 'البريد الإلكتروني غير صالح'}), 400
        
        # التحقق من قوة كلمة المرور
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'message': message}), 400
        
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
            is_verified=False  # سيتم التحقق لاحقاً
        )
        new_user.set_password(password)
        
        # إنشاء رمز التحقق
        verification_token = new_user.generate_verification_token()
        new_user.verification_token = verification_token
        
        db.session.add(new_user)
        db.session.commit()
        
        # إنشاء الملف الشخصي
        profile = UserProfile(user_id=new_user.id)
        db.session.add(profile)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء الحساب بنجاح. يرجى التحقق من البريد الإلكتروني',
            'user': new_user.to_dict(),
            'verification_token': verification_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء الحساب'}), 500

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """التحقق من البريد الإلكتروني"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'message': 'رمز التحقق مطلوب'}), 400
        
        # فك تشفير الرمز
        user = User.verify_token(token)
        if not user:
            return jsonify({'message': 'رمز التحقق غير صالح أو منتهي الصلاحية'}), 400
        
        # تفعيل المستخدم
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        
        return jsonify({'message': 'تم التحقق من البريد الإلكتروني بنجاح'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Email verification error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في التحقق من البريد الإلكتروني'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """تغيير كلمة المرور"""
    try:
        data = request.get_json()
        
        current_password = data.get('currentPassword', '')
        new_password = data.get('newPassword', '')
        confirm_password = data.get('confirmPassword', '')
        
        # التحقق من البيانات المطلوبة
        if not current_password or not new_password or not confirm_password:
            return jsonify({'message': 'جميع الحقول مطلوبة'}), 400
        
        # التحقق من كلمة المرور الحالية
        if not current_user.check_password(current_password):
            return jsonify({'message': 'كلمة المرور الحالية غير صحيحة'}), 400
        
        # التحقق من تطابق كلمة المرور الجديدة
        if new_password != confirm_password:
            return jsonify({'message': 'كلمة المرور الجديدة غير متطابقة'}), 400
        
        # التحقق من قوة كلمة المرور الجديدة
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'message': message}), 400
        
        # تحديث كلمة المرور
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'تم تغيير كلمة المرور بنجاح'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تغيير كلمة المرور'}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """نسيان كلمة المرور"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'message': 'البريد الإلكتروني مطلوب'}), 400
        
        if not validate_email(email):
            return jsonify({'message': 'البريد الإلكتروني غير صالح'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        # إرسال رسالة نجاح حتى لو لم يكن المستخدم موجود (لأسباب أمنية)
        if user:
            reset_token = user.generate_reset_token()
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # هنا يمكن إرسال البريد الإلكتروني
            # send_reset_email(user.email, reset_token)
        
        return jsonify({
            'message': 'إذا كان البريد الإلكتروني موجود، ستتلقى رسالة لإعادة تعيين كلمة المرور'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في معالجة الطلب'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """إعادة تعيين كلمة المرور"""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('newPassword')
        confirm_password = data.get('confirmPassword')
        
        if not token or not new_password or not confirm_password:
            return jsonify({'message': 'جميع الحقول مطلوبة'}), 400
        
        if new_password != confirm_password:
            return jsonify({'message': 'كلمة المرور غير متطابقة'}), 400
        
        # التحقق من قوة كلمة المرور
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'message': message}), 400
        
        # التحقق من الرمز
        user = User.verify_reset_token(token)
        if not user:
            return jsonify({'message': 'رمز إعادة التعيين غير صالح أو منتهي الصلاحية'}), 400
        
        # تحديث كلمة المرور
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        return jsonify({'message': 'تم إعادة تعيين كلمة المرور بنجاح'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Reset password error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إعادة تعيين كلمة المرور'}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """الحصول على الملف الشخصي"""
    try:
        profile = current_user.profile
        if not profile:
            # إنشاء ملف شخصي إذا لم يكن موجود
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
            db.session.commit()
        
        return jsonify({
            'user': current_user.to_dict(),
            'profile': profile.to_dict() if profile else None
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get profile error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الملف الشخصي'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """تحديث الملف الشخصي"""
    try:
        data = request.get_json()
        
        # تحديث بيانات المستخدم الأساسية
        if 'name' in data:
            current_user.name = data['name'].strip()
        if 'department' in data:
            current_user.department = data['department'].strip()
        if 'phone' in data:
            current_user.phone = data['phone'].strip()
        
        # تحديث الملف الشخصي
        profile = current_user.profile
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
        
        if 'bio' in data:
            profile.bio = data['bio']
        if 'address' in data:
            profile.address = data['address']
        if 'emergency_contact' in data:
            profile.emergency_contact = data['emergency_contact']
        if 'emergency_phone' in data:
            profile.emergency_phone = data['emergency_phone']
        if 'certifications' in data:
            profile.certifications = data['certifications']
        if 'training_records' in data:
            profile.training_records = data['training_records']
        if 'preferences' in data:
            profile.preferences = data['preferences']
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث الملف الشخصي بنجاح',
            'user': current_user.to_dict(),
            'profile': profile.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update profile error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تحديث الملف الشخصي'}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """تسجيل الخروج"""
    try:
        # حذف جلسات المستخدم
        UserSession.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({'message': 'تم تسجيل الخروج بنجاح'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تسجيل الخروج'}), 500

@auth_bp.route('/validate-token', methods=['POST'])
def validate_token():
    """التحقق من صحة الرمز المميز"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'valid': False, 'message': 'الرمز المميز مطلوب'}), 400
        
        user = User.verify_token(token)
        if user and user.is_active:
            return jsonify({
                'valid': True,
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({
                'valid': False,
                'message': 'الرمز المميز غير صالح أو منتهي الصلاحية'
            }), 401
            
    except Exception as e:
        current_app.logger.error(f"Token validation error: {str(e)}")
        return jsonify({
            'valid': False,
            'message': 'حدث خطأ في التحقق من الرمز المميز'
        }), 500

