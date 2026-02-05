from flask import Blueprint, jsonify, request, current_app
from src.models.user import Device, Inspection, MaintenanceTask, db
from src.routes.auth import token_required
from datetime import datetime, timedelta

devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/devices', methods=['GET'])
@token_required
def get_devices(current_user):
    """الحصول على قائمة الأجهزة"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        device_type = request.args.get('type', '')
        location = request.args.get('location', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        
        # بناء الاستعلام
        query = Device.query
        
        # تصفية حسب النوع
        if device_type:
            query = query.filter(Device.type == device_type)
        
        # تصفية حسب الموقع
        if location:
            query = query.filter(Device.location.contains(location))
        
        # تصفية حسب الحالة
        if status:
            query = query.filter(Device.status == status)
        
        # البحث
        if search:
            query = query.filter(
                (Device.name.contains(search)) |
                (Device.location.contains(search)) |
                (Device.serial_number.contains(search))
            )
        
        # ترتيب النتائج
        query = query.order_by(Device.name.asc())
        
        # تطبيق التصفح
        devices = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        devices_data = []
        for device in devices.items:
            # حساب آخر تشييك
            last_inspection = Inspection.query.filter_by(
                device_id=device.id
            ).order_by(Inspection.inspection_date.desc()).first()
            
            # حساب المهام المعلقة
            pending_tasks = MaintenanceTask.query.filter_by(
                device_id=device.id,
                status='pending'
            ).count()
            
            device_data = {
                'id': device.id,
                'name': device.name,
                'type': device.type,
                'location': device.location,
                'serial_number': device.serial_number,
                'installation_date': device.installation_date.isoformat() if device.installation_date else None,
                'last_maintenance': device.last_maintenance.isoformat() if device.last_maintenance else None,
                'next_maintenance': device.next_maintenance.isoformat() if device.next_maintenance else None,
                'status': device.status,
                'created_at': device.created_at.isoformat(),
                'last_inspection': {
                    'date': last_inspection.inspection_date.isoformat() if last_inspection else None,
                    'status': last_inspection.status if last_inspection else None,
                    'inspector': last_inspection.inspector.name if last_inspection else None
                },
                'pending_tasks': pending_tasks,
                'maintenance_due': device.next_maintenance and device.next_maintenance <= datetime.utcnow().date() + timedelta(days=7),
                'can_edit': current_user.can_manage_users()
            }
            devices_data.append(device_data)
        
        return jsonify({
            'devices': devices_data,
            'pagination': {
                'page': page,
                'pages': devices.pages,
                'per_page': per_page,
                'total': devices.total,
                'has_next': devices.has_next,
                'has_prev': devices.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get devices error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الأجهزة'}), 500

@devices_bp.route('/devices', methods=['POST'])
@token_required
def create_device(current_user):
    """إنشاء جهاز جديد"""
    try:
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لإضافة أجهزة'}), 403
        
        data = request.get_json()
        
        name = data.get('name', '').strip()
        device_type = data.get('type', '').strip()
        location = data.get('location', '').strip()
        serial_number = data.get('serial_number', '').strip()
        installation_date = data.get('installation_date')
        next_maintenance = data.get('next_maintenance')
        
        # التحقق من البيانات المطلوبة
        if not name or not device_type or not location:
            return jsonify({'message': 'الاسم والنوع والموقع مطلوبة'}), 400
        
        # التحقق من عدم تكرار الرقم التسلسلي
        if serial_number:
            existing_device = Device.query.filter_by(serial_number=serial_number).first()
            if existing_device:
                return jsonify({'message': 'الرقم التسلسلي مستخدم مسبقاً'}), 409
        
        # تحويل التواريخ
        installation_date_obj = None
        if installation_date:
            try:
                installation_date_obj = datetime.fromisoformat(installation_date.replace('Z', '+00:00')).date()
            except ValueError:
                pass
        
        next_maintenance_obj = None
        if next_maintenance:
            try:
                next_maintenance_obj = datetime.fromisoformat(next_maintenance.replace('Z', '+00:00')).date()
            except ValueError:
                pass
        
        # إنشاء الجهاز الجديد
        new_device = Device(
            name=name,
            type=device_type,
            location=location,
            serial_number=serial_number,
            installation_date=installation_date_obj,
            next_maintenance=next_maintenance_obj,
            status='active'
        )
        
        db.session.add(new_device)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء الجهاز بنجاح',
            'device': {
                'id': new_device.id,
                'name': new_device.name,
                'type': new_device.type,
                'location': new_device.location,
                'serial_number': new_device.serial_number,
                'installation_date': new_device.installation_date.isoformat() if new_device.installation_date else None,
                'next_maintenance': new_device.next_maintenance.isoformat() if new_device.next_maintenance else None,
                'status': new_device.status,
                'created_at': new_device.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create device error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء الجهاز'}), 500

@devices_bp.route('/devices/<int:device_id>', methods=['GET'])
@token_required
def get_device(current_user, device_id):
    """الحصول على جهاز معين"""
    try:
        device = Device.query.get_or_404(device_id)
        
        # جلب آخر التشييكات
        recent_inspections = Inspection.query.filter_by(
            device_id=device.id
        ).order_by(Inspection.inspection_date.desc()).limit(5).all()
        
        # جلب مهام الصيانة
        maintenance_tasks = MaintenanceTask.query.filter_by(
            device_id=device.id
        ).order_by(MaintenanceTask.scheduled_date.desc()).limit(5).all()
        
        return jsonify({
            'device': {
                'id': device.id,
                'name': device.name,
                'type': device.type,
                'location': device.location,
                'serial_number': device.serial_number,
                'installation_date': device.installation_date.isoformat() if device.installation_date else None,
                'last_maintenance': device.last_maintenance.isoformat() if device.last_maintenance else None,
                'next_maintenance': device.next_maintenance.isoformat() if device.next_maintenance else None,
                'status': device.status,
                'created_at': device.created_at.isoformat(),
                'can_edit': current_user.can_manage_users()
            },
            'recent_inspections': [
                {
                    'id': inspection.id,
                    'inspection_date': inspection.inspection_date.isoformat(),
                    'status': inspection.status,
                    'inspector_name': inspection.inspector.name,
                    'notes': inspection.notes[:100] + '...' if inspection.notes and len(inspection.notes) > 100 else inspection.notes
                } for inspection in recent_inspections
            ],
            'maintenance_tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'priority': task.priority,
                    'status': task.status,
                    'scheduled_date': task.scheduled_date.isoformat() if task.scheduled_date else None,
                    'assigned_user_name': task.assigned_user.name
                } for task in maintenance_tasks
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get device error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الجهاز'}), 500

@devices_bp.route('/devices/<int:device_id>', methods=['PUT'])
@token_required
def update_device(current_user, device_id):
    """تحديث جهاز"""
    try:
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لتعديل الأجهزة'}), 403
        
        device = Device.query.get_or_404(device_id)
        data = request.get_json()
        
        # تحديث البيانات
        if 'name' in data and data['name'].strip():
            device.name = data['name'].strip()
        
        if 'type' in data and data['type'].strip():
            device.type = data['type'].strip()
        
        if 'location' in data and data['location'].strip():
            device.location = data['location'].strip()
        
        if 'serial_number' in data:
            serial_number = data['serial_number'].strip()
            if serial_number and serial_number != device.serial_number:
                # التحقق من عدم تكرار الرقم التسلسلي
                existing_device = Device.query.filter_by(serial_number=serial_number).first()
                if existing_device:
                    return jsonify({'message': 'الرقم التسلسلي مستخدم مسبقاً'}), 409
                device.serial_number = serial_number
        
        if 'installation_date' in data:
            try:
                device.installation_date = datetime.fromisoformat(
                    data['installation_date'].replace('Z', '+00:00')
                ).date()
            except ValueError:
                pass
        
        if 'last_maintenance' in data:
            try:
                device.last_maintenance = datetime.fromisoformat(
                    data['last_maintenance'].replace('Z', '+00:00')
                ).date()
            except ValueError:
                pass
        
        if 'next_maintenance' in data:
            try:
                device.next_maintenance = datetime.fromisoformat(
                    data['next_maintenance'].replace('Z', '+00:00')
                ).date()
            except ValueError:
                pass
        
        if 'status' in data:
            device.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث الجهاز بنجاح',
            'device': {
                'id': device.id,
                'name': device.name,
                'type': device.type,
                'location': device.location,
                'serial_number': device.serial_number,
                'installation_date': device.installation_date.isoformat() if device.installation_date else None,
                'last_maintenance': device.last_maintenance.isoformat() if device.last_maintenance else None,
                'next_maintenance': device.next_maintenance.isoformat() if device.next_maintenance else None,
                'status': device.status
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update device error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تحديث الجهاز'}), 500

@devices_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@token_required
def delete_device(current_user, device_id):
    """حذف جهاز"""
    try:
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لحذف الأجهزة'}), 403
        
        device = Device.query.get_or_404(device_id)
        
        # التحقق من وجود تشييكات أو مهام صيانة مرتبطة
        inspections_count = Inspection.query.filter_by(device_id=device.id).count()
        tasks_count = MaintenanceTask.query.filter_by(device_id=device.id).count()
        
        if inspections_count > 0 or tasks_count > 0:
            return jsonify({
                'message': f'لا يمكن حذف الجهاز لوجود {inspections_count} تشييك و {tasks_count} مهمة صيانة مرتبطة به'
            }), 400
        
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({'message': 'تم حذف الجهاز بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete device error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في حذف الجهاز'}), 500

@devices_bp.route('/devices/types', methods=['GET'])
@token_required
def get_device_types(current_user):
    """الحصول على أنواع الأجهزة"""
    try:
        device_types = [
            {'value': 'fire_extinguisher', 'label': 'طفاية حريق'},
            {'value': 'smoke_detector', 'label': 'كاشف دخان'},
            {'value': 'fire_alarm', 'label': 'جهاز إنذار حريق'},
            {'value': 'sprinkler_system', 'label': 'نظام الرش'},
            {'value': 'fire_hose', 'label': 'خرطوم حريق'},
            {'value': 'emergency_exit', 'label': 'مخرج طوارئ'},
            {'value': 'emergency_lighting', 'label': 'إضاءة طوارئ'},
            {'value': 'fire_door', 'label': 'باب حريق'},
            {'value': 'fire_pump', 'label': 'مضخة حريق'},
            {'value': 'fire_panel', 'label': 'لوحة تحكم حريق'}
        ]
        
        return jsonify({'device_types': device_types}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get device types error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب أنواع الأجهزة'}), 500

@devices_bp.route('/devices/locations', methods=['GET'])
@token_required
def get_device_locations(current_user):
    """الحصول على مواقع الأجهزة"""
    try:
        # الحصول على المواقع من قاعدة البيانات
        locations_query = db.session.query(Device.location).filter(
            Device.location.isnot(None),
            Device.location != ''
        ).distinct().all()
        
        locations = [loc[0] for loc in locations_query if loc[0]]
        
        # إضافة مواقع افتراضية إذا لم تكن موجودة
        default_locations = [
            'الطابق الأول',
            'الطابق الثاني',
            'الطابق الثالث',
            'القبو',
            'المطبخ',
            'المختبر',
            'غرفة العمليات',
            'العيادة الخارجية',
            'قسم الطوارئ',
            'المخزن',
            'الممر الرئيسي',
            'مدخل المبنى'
        ]
        
        for location in default_locations:
            if location not in locations:
                locations.append(location)
        
        return jsonify({'locations': sorted(locations)}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get device locations error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب مواقع الأجهزة'}), 500

@devices_bp.route('/devices/stats', methods=['GET'])
@token_required
def get_devices_stats(current_user):
    """الحصول على إحصائيات الأجهزة"""
    try:
        # إحصائيات عامة
        total_devices = Device.query.count()
        active_devices = Device.query.filter_by(status='active').count()
        inactive_devices = Device.query.filter_by(status='inactive').count()
        
        # إحصائيات حسب النوع
        type_stats = db.session.query(
            Device.type,
            db.func.count(Device.id).label('count')
        ).filter_by(status='active').group_by(Device.type).all()
        
        # إحصائيات حسب الموقع
        location_stats = db.session.query(
            Device.location,
            db.func.count(Device.id).label('count')
        ).filter(
            Device.status == 'active',
            Device.location.isnot(None),
            Device.location != ''
        ).group_by(Device.location).all()
        
        # الأجهزة التي تحتاج صيانة قريباً
        upcoming_maintenance = Device.query.filter(
            Device.next_maintenance.isnot(None),
            Device.next_maintenance <= datetime.utcnow().date() + timedelta(days=30),
            Device.status == 'active'
        ).count()
        
        # الأجهزة المتأخرة في الصيانة
        overdue_maintenance = Device.query.filter(
            Device.next_maintenance.isnot(None),
            Device.next_maintenance < datetime.utcnow().date(),
            Device.status == 'active'
        ).count()
        
        # آخر التشييكات
        recent_inspections = db.session.query(
            Device.name,
            Device.location,
            Inspection.status,
            Inspection.inspection_date
        ).join(Inspection).order_by(
            Inspection.inspection_date.desc()
        ).limit(10).all()
        
        return jsonify({
            'total_devices': total_devices,
            'active_devices': active_devices,
            'inactive_devices': inactive_devices,
            'upcoming_maintenance': upcoming_maintenance,
            'overdue_maintenance': overdue_maintenance,
            'type_distribution': [
                {'type': device_type, 'count': count} for device_type, count in type_stats
            ],
            'location_distribution': [
                {'location': location, 'count': count} for location, count in location_stats
            ],
            'recent_inspections': [
                {
                    'device_name': name,
                    'location': location,
                    'status': status,
                    'inspection_date': inspection_date.isoformat()
                } for name, location, status, inspection_date in recent_inspections
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get devices stats error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب إحصائيات الأجهزة'}), 500

@devices_bp.route('/devices/bulk-create', methods=['POST'])
@token_required
def bulk_create_devices(current_user):
    """إنشاء أجهزة متعددة"""
    try:
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لإضافة أجهزة'}), 403
        
        data = request.get_json()
        devices_data = data.get('devices', [])
        
        if not devices_data:
            return jsonify({'message': 'لم يتم تحديد أي أجهزة للإنشاء'}), 400
        
        created_devices = []
        errors = []
        
        for device_data in devices_data:
            try:
                name = device_data.get('name', '').strip()
                device_type = device_data.get('type', '').strip()
                location = device_data.get('location', '').strip()
                serial_number = device_data.get('serial_number', '').strip()
                
                if not name or not device_type or not location:
                    errors.append('الاسم والنوع والموقع مطلوبة')
                    continue
                
                # التحقق من عدم تكرار الرقم التسلسلي
                if serial_number:
                    existing_device = Device.query.filter_by(serial_number=serial_number).first()
                    if existing_device:
                        errors.append(f'الرقم التسلسلي {serial_number} مستخدم مسبقاً')
                        continue
                
                # إنشاء الجهاز
                new_device = Device(
                    name=name,
                    type=device_type,
                    location=location,
                    serial_number=serial_number,
                    status='active'
                )
                
                db.session.add(new_device)
                created_devices.append({
                    'name': name,
                    'type': device_type,
                    'location': location
                })
                
            except Exception as e:
                errors.append(f'خطأ في إنشاء الجهاز {name}: {str(e)}')
        
        db.session.commit()
        
        return jsonify({
            'message': f'تم إنشاء {len(created_devices)} جهاز بنجاح',
            'created_devices': created_devices,
            'errors': errors,
            'total_created': len(created_devices),
            'total_errors': len(errors)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bulk create devices error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء الأجهزة'}), 500

