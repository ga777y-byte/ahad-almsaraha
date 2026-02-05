from flask import Blueprint, jsonify, request, current_app
from src.models.user import Inspection, Device, User, db
from src.routes.auth import token_required
from datetime import datetime, timedelta
import json
import os

inspections_bp = Blueprint('inspections', __name__)

@inspections_bp.route('/inspections', methods=['GET'])
@token_required
def get_inspections(current_user):
    """الحصول على قائمة التشييكات"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        device_id = request.args.get('device_id', type=int)
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        inspector_id = request.args.get('inspector_id', type=int)
        
        # بناء الاستعلام
        query = db.session.query(
            Inspection,
            Device.name.label('device_name'),
            Device.location.label('device_location'),
            User.name.label('inspector_name')
        ).join(Device).join(User)
        
        # تصفية حسب الجهاز
        if device_id:
            query = query.filter(Inspection.device_id == device_id)
        
        # تصفية حسب الحالة
        if status:
            query = query.filter(Inspection.status == status)
        
        # تصفية حسب المفتش
        if inspector_id:
            query = query.filter(Inspection.inspector_id == inspector_id)
        
        # تصفية حسب التاريخ
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(Inspection.inspection_date >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(Inspection.inspection_date <= to_date)
            except ValueError:
                pass
        
        # ترتيب النتائج
        query = query.order_by(Inspection.inspection_date.desc())
        
        # تطبيق التصفح
        inspections = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        inspections_data = []
        for inspection, device_name, device_location, inspector_name in inspections.items:
            inspection_data = {
                'id': inspection.id,
                'device_id': inspection.device_id,
                'device_name': device_name,
                'device_location': device_location,
                'inspector_id': inspection.inspector_id,
                'inspector_name': inspector_name,
                'inspection_date': inspection.inspection_date.isoformat(),
                'status': inspection.status,
                'notes': inspection.notes,
                'images': json.loads(inspection.images) if inspection.images else [],
                'created_at': inspection.created_at.isoformat(),
                'can_edit': inspection.inspector_id == current_user.id or current_user.can_manage_users()
            }
            inspections_data.append(inspection_data)
        
        return jsonify({
            'inspections': inspections_data,
            'pagination': {
                'page': page,
                'pages': inspections.pages,
                'per_page': per_page,
                'total': inspections.total,
                'has_next': inspections.has_next,
                'has_prev': inspections.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get inspections error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب التشييكات'}), 500

@inspections_bp.route('/inspections', methods=['POST'])
@token_required
def create_inspection(current_user):
    """إنشاء تشييك جديد"""
    try:
        data = request.get_json()
        
        device_id = data.get('device_id')
        status = data.get('status', 'good')
        notes = data.get('notes', '')
        images = data.get('images', [])
        inspection_date = data.get('inspection_date')
        
        # التحقق من البيانات المطلوبة
        if not device_id:
            return jsonify({'message': 'معرف الجهاز مطلوب'}), 400
        
        # التحقق من وجود الجهاز
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'message': 'الجهاز غير موجود'}), 404
        
        # تحديد تاريخ التشييك
        if inspection_date:
            try:
                inspection_datetime = datetime.fromisoformat(inspection_date.replace('Z', '+00:00'))
            except ValueError:
                inspection_datetime = datetime.utcnow()
        else:
            inspection_datetime = datetime.utcnow()
        
        # إنشاء التشييك الجديد
        new_inspection = Inspection(
            device_id=device_id,
            inspector_id=current_user.id,
            inspection_date=inspection_datetime,
            status=status,
            notes=notes,
            images=json.dumps(images) if images else None
        )
        
        db.session.add(new_inspection)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء التشييك بنجاح',
            'inspection': {
                'id': new_inspection.id,
                'device_id': new_inspection.device_id,
                'device_name': device.name,
                'inspector_id': new_inspection.inspector_id,
                'inspector_name': current_user.name,
                'inspection_date': new_inspection.inspection_date.isoformat(),
                'status': new_inspection.status,
                'notes': new_inspection.notes,
                'images': json.loads(new_inspection.images) if new_inspection.images else [],
                'created_at': new_inspection.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create inspection error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء التشييك'}), 500

@inspections_bp.route('/inspections/<int:inspection_id>', methods=['GET'])
@token_required
def get_inspection(current_user, inspection_id):
    """الحصول على تشييك معين"""
    try:
        inspection_data = db.session.query(
            Inspection,
            Device.name.label('device_name'),
            Device.location.label('device_location'),
            Device.type.label('device_type'),
            User.name.label('inspector_name')
        ).join(Device).join(User).filter(Inspection.id == inspection_id).first()
        
        if not inspection_data:
            return jsonify({'message': 'التشييك غير موجود'}), 404
        
        inspection, device_name, device_location, device_type, inspector_name = inspection_data
        
        return jsonify({
            'inspection': {
                'id': inspection.id,
                'device_id': inspection.device_id,
                'device_name': device_name,
                'device_location': device_location,
                'device_type': device_type,
                'inspector_id': inspection.inspector_id,
                'inspector_name': inspector_name,
                'inspection_date': inspection.inspection_date.isoformat(),
                'status': inspection.status,
                'notes': inspection.notes,
                'images': json.loads(inspection.images) if inspection.images else [],
                'created_at': inspection.created_at.isoformat(),
                'can_edit': inspection.inspector_id == current_user.id or current_user.can_manage_users()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get inspection error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب التشييك'}), 500

@inspections_bp.route('/inspections/<int:inspection_id>', methods=['PUT'])
@token_required
def update_inspection(current_user, inspection_id):
    """تحديث تشييك"""
    try:
        inspection = Inspection.query.get_or_404(inspection_id)
        
        # التحقق من الصلاحيات
        if inspection.inspector_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لتعديل هذا التشييك'}), 403
        
        data = request.get_json()
        
        # تحديث البيانات
        if 'status' in data:
            inspection.status = data['status']
        
        if 'notes' in data:
            inspection.notes = data['notes']
        
        if 'images' in data:
            inspection.images = json.dumps(data['images'])
        
        if 'inspection_date' in data:
            try:
                inspection.inspection_date = datetime.fromisoformat(
                    data['inspection_date'].replace('Z', '+00:00')
                )
            except ValueError:
                pass
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث التشييك بنجاح',
            'inspection': {
                'id': inspection.id,
                'status': inspection.status,
                'notes': inspection.notes,
                'images': json.loads(inspection.images) if inspection.images else [],
                'inspection_date': inspection.inspection_date.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update inspection error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تحديث التشييك'}), 500

@inspections_bp.route('/inspections/<int:inspection_id>', methods=['DELETE'])
@token_required
def delete_inspection(current_user, inspection_id):
    """حذف تشييك"""
    try:
        inspection = Inspection.query.get_or_404(inspection_id)
        
        # التحقق من الصلاحيات
        if inspection.inspector_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لحذف هذا التشييك'}), 403
        
        db.session.delete(inspection)
        db.session.commit()
        
        return jsonify({'message': 'تم حذف التشييك بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete inspection error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في حذف التشييك'}), 500

@inspections_bp.route('/inspections/stats', methods=['GET'])
@token_required
def get_inspections_stats(current_user):
    """الحصول على إحصائيات التشييكات"""
    try:
        # إحصائيات عامة
        total_inspections = Inspection.query.count()
        today_inspections = Inspection.query.filter(
            db.func.date(Inspection.inspection_date) == datetime.utcnow().date()
        ).count()
        
        # إحصائيات حسب الحالة
        status_stats = db.session.query(
            Inspection.status,
            db.func.count(Inspection.id).label('count')
        ).group_by(Inspection.status).all()
        
        # إحصائيات حسب المفتش
        inspector_stats = db.session.query(
            User.name,
            db.func.count(Inspection.id).label('count')
        ).join(Inspection).group_by(User.id, User.name).all()
        
        # إحصائيات الأسبوع الماضي
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_inspections = db.session.query(
            db.func.date(Inspection.inspection_date).label('date'),
            db.func.count(Inspection.id).label('count')
        ).filter(
            Inspection.inspection_date >= week_ago
        ).group_by(
            db.func.date(Inspection.inspection_date)
        ).order_by('date').all()
        
        # إحصائيات الأجهزة الأكثر تشييكاً
        device_stats = db.session.query(
            Device.name,
            Device.location,
            db.func.count(Inspection.id).label('count')
        ).join(Inspection).group_by(
            Device.id, Device.name, Device.location
        ).order_by(db.func.count(Inspection.id).desc()).limit(10).all()
        
        return jsonify({
            'total_inspections': total_inspections,
            'today_inspections': today_inspections,
            'status_distribution': [
                {'status': status, 'count': count} for status, count in status_stats
            ],
            'inspector_performance': [
                {'inspector': name, 'count': count} for name, count in inspector_stats
            ],
            'weekly_trend': [
                {
                    'date': date.isoformat(),
                    'count': count
                } for date, count in weekly_inspections
            ],
            'top_devices': [
                {
                    'device_name': name,
                    'location': location,
                    'inspection_count': count
                } for name, location, count in device_stats
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get inspections stats error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب إحصائيات التشييكات'}), 500

@inspections_bp.route('/inspections/templates', methods=['GET'])
@token_required
def get_inspection_templates(current_user):
    """الحصول على قوالب التشييك"""
    try:
        templates = [
            {
                'id': 'fire_extinguisher',
                'name': 'طفاية حريق',
                'fields': [
                    {'name': 'pressure_gauge', 'label': 'مقياس الضغط', 'type': 'select', 'options': ['جيد', 'متوسط', 'ضعيف']},
                    {'name': 'safety_pin', 'label': 'دبوس الأمان', 'type': 'select', 'options': ['موجود', 'مفقود']},
                    {'name': 'hose_condition', 'label': 'حالة الخرطوم', 'type': 'select', 'options': ['جيد', 'متضرر']},
                    {'name': 'label_readable', 'label': 'وضوح الملصق', 'type': 'select', 'options': ['واضح', 'غير واضح']},
                    {'name': 'accessibility', 'label': 'سهولة الوصول', 'type': 'select', 'options': ['سهل', 'صعب', 'مسدود']}
                ]
            },
            {
                'id': 'smoke_detector',
                'name': 'كاشف دخان',
                'fields': [
                    {'name': 'led_indicator', 'label': 'مؤشر LED', 'type': 'select', 'options': ['يعمل', 'لا يعمل']},
                    {'name': 'test_button', 'label': 'زر الاختبار', 'type': 'select', 'options': ['يعمل', 'لا يعمل']},
                    {'name': 'cleanliness', 'label': 'النظافة', 'type': 'select', 'options': ['نظيف', 'متسخ']},
                    {'name': 'mounting', 'label': 'التثبيت', 'type': 'select', 'options': ['محكم', 'مفكوك']}
                ]
            },
            {
                'id': 'fire_alarm',
                'name': 'جهاز إنذار حريق',
                'fields': [
                    {'name': 'power_status', 'label': 'حالة الطاقة', 'type': 'select', 'options': ['يعمل', 'لا يعمل']},
                    {'name': 'sound_test', 'label': 'اختبار الصوت', 'type': 'select', 'options': ['واضح', 'ضعيف', 'لا يعمل']},
                    {'name': 'display_screen', 'label': 'شاشة العرض', 'type': 'select', 'options': ['تعمل', 'لا تعمل']},
                    {'name': 'backup_battery', 'label': 'البطارية الاحتياطية', 'type': 'select', 'options': ['جيدة', 'ضعيفة', 'تحتاج استبدال']}
                ]
            },
            {
                'id': 'emergency_exit',
                'name': 'مخرج طوارئ',
                'fields': [
                    {'name': 'door_operation', 'label': 'تشغيل الباب', 'type': 'select', 'options': ['سهل', 'صعب', 'مسدود']},
                    {'name': 'exit_sign', 'label': 'لافتة المخرج', 'type': 'select', 'options': ['مضيئة', 'غير مضيئة', 'مفقودة']},
                    {'name': 'pathway_clear', 'label': 'وضوح المسار', 'type': 'select', 'options': ['واضح', 'مسدود جزئياً', 'مسدود كلياً']},
                    {'name': 'emergency_lighting', 'label': 'الإضاءة الطارئة', 'type': 'select', 'options': ['تعمل', 'لا تعمل']}
                ]
            }
        ]
        
        return jsonify({
            'templates': templates,
            'message': 'تم جلب قوالب التشييك بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get inspection templates error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب قوالب التشييك'}), 500

@inspections_bp.route('/inspections/bulk-create', methods=['POST'])
@token_required
def bulk_create_inspections(current_user):
    """إنشاء تشييكات متعددة"""
    try:
        data = request.get_json()
        inspections_data = data.get('inspections', [])
        
        if not inspections_data:
            return jsonify({'message': 'لم يتم تحديد أي تشييكات للإنشاء'}), 400
        
        created_inspections = []
        errors = []
        
        for inspection_data in inspections_data:
            try:
                device_id = inspection_data.get('device_id')
                status = inspection_data.get('status', 'good')
                notes = inspection_data.get('notes', '')
                images = inspection_data.get('images', [])
                
                if not device_id:
                    errors.append('معرف الجهاز مطلوب')
                    continue
                
                # التحقق من وجود الجهاز
                device = Device.query.get(device_id)
                if not device:
                    errors.append(f'الجهاز {device_id} غير موجود')
                    continue
                
                # إنشاء التشييك
                new_inspection = Inspection(
                    device_id=device_id,
                    inspector_id=current_user.id,
                    inspection_date=datetime.utcnow(),
                    status=status,
                    notes=notes,
                    images=json.dumps(images) if images else None
                )
                
                db.session.add(new_inspection)
                created_inspections.append({
                    'device_id': device_id,
                    'device_name': device.name,
                    'status': status
                })
                
            except Exception as e:
                errors.append(f'خطأ في إنشاء تشييك للجهاز {device_id}: {str(e)}')
        
        db.session.commit()
        
        return jsonify({
            'message': f'تم إنشاء {len(created_inspections)} تشييك بنجاح',
            'created_inspections': created_inspections,
            'errors': errors,
            'total_created': len(created_inspections),
            'total_errors': len(errors)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bulk create inspections error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء التشييكات'}), 500

