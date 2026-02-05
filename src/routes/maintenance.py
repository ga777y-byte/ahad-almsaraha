from flask import Blueprint, jsonify, request, current_app
from src.models.user import MaintenanceTask, Device, User, db
from src.routes.auth import token_required
from datetime import datetime, timedelta
import json

maintenance_bp = Blueprint('maintenance', __name__)

@maintenance_bp.route('/maintenance', methods=['GET'])
@token_required
def get_maintenance_tasks(current_user):
    """الحصول على قائمة مهام الصيانة"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        device_id = request.args.get('device_id', type=int)
        status = request.args.get('status', '')
        priority = request.args.get('priority', '')
        assigned_user_id = request.args.get('assigned_user_id', type=int)
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # بناء الاستعلام
        query = db.session.query(
            MaintenanceTask,
            Device.name.label('device_name'),
            Device.location.label('device_location'),
            User.name.label('assigned_user_name')
        ).join(Device).join(User)
        
        # تصفية حسب الجهاز
        if device_id:
            query = query.filter(MaintenanceTask.device_id == device_id)
        
        # تصفية حسب الحالة
        if status:
            query = query.filter(MaintenanceTask.status == status)
        
        # تصفية حسب الأولوية
        if priority:
            query = query.filter(MaintenanceTask.priority == priority)
        
        # تصفية حسب المستخدم المكلف
        if assigned_user_id:
            query = query.filter(MaintenanceTask.assigned_user_id == assigned_user_id)
        
        # تصفية حسب التاريخ
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(MaintenanceTask.scheduled_date >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(MaintenanceTask.scheduled_date <= to_date)
            except ValueError:
                pass
        
        # ترتيب النتائج
        query = query.order_by(MaintenanceTask.scheduled_date.asc())
        
        # تطبيق التصفح
        tasks = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        tasks_data = []
        for task, device_name, device_location, assigned_user_name in tasks.items:
            task_data = {
                'id': task.id,
                'device_id': task.device_id,
                'device_name': device_name,
                'device_location': device_location,
                'assigned_user_id': task.assigned_user_id,
                'assigned_user_name': assigned_user_name,
                'title': task.title,
                'description': task.description,
                'priority': task.priority,
                'status': task.status,
                'scheduled_date': task.scheduled_date.isoformat() if task.scheduled_date else None,
                'completed_date': task.completed_date.isoformat() if task.completed_date else None,
                'notes': task.notes,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'is_overdue': task.scheduled_date and task.scheduled_date < datetime.utcnow() and task.status == 'pending',
                'can_edit': task.assigned_user_id == current_user.id or current_user.can_manage_users()
            }
            tasks_data.append(task_data)
        
        return jsonify({
            'tasks': tasks_data,
            'pagination': {
                'page': page,
                'pages': tasks.pages,
                'per_page': per_page,
                'total': tasks.total,
                'has_next': tasks.has_next,
                'has_prev': tasks.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get maintenance tasks error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب مهام الصيانة'}), 500

@maintenance_bp.route('/maintenance', methods=['POST'])
@token_required
def create_maintenance_task(current_user):
    """إنشاء مهمة صيانة جديدة"""
    try:
        data = request.get_json()
        
        device_id = data.get('device_id')
        assigned_user_id = data.get('assigned_user_id')
        title = data.get('title', '')
        description = data.get('description', '')
        priority = data.get('priority', 'medium')
        scheduled_date = data.get('scheduled_date')
        
        # التحقق من البيانات المطلوبة
        if not device_id or not assigned_user_id or not title:
            return jsonify({'message': 'معرف الجهاز والمستخدم المكلف والعنوان مطلوبة'}), 400
        
        # التحقق من وجود الجهاز
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'message': 'الجهاز غير موجود'}), 404
        
        # التحقق من وجود المستخدم المكلف
        assigned_user = User.query.get(assigned_user_id)
        if not assigned_user:
            return jsonify({'message': 'المستخدم المكلف غير موجود'}), 404
        
        # تحديد تاريخ الجدولة
        if scheduled_date:
            try:
                scheduled_datetime = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
            except ValueError:
                scheduled_datetime = datetime.utcnow() + timedelta(days=1)
        else:
            scheduled_datetime = datetime.utcnow() + timedelta(days=1)
        
        # إنشاء مهمة الصيانة الجديدة
        new_task = MaintenanceTask(
            device_id=device_id,
            assigned_user_id=assigned_user_id,
            title=title,
            description=description,
            priority=priority,
            scheduled_date=scheduled_datetime,
            status='pending'
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء مهمة الصيانة بنجاح',
            'task': {
                'id': new_task.id,
                'device_id': new_task.device_id,
                'device_name': device.name,
                'assigned_user_id': new_task.assigned_user_id,
                'assigned_user_name': assigned_user.name,
                'title': new_task.title,
                'description': new_task.description,
                'priority': new_task.priority,
                'status': new_task.status,
                'scheduled_date': new_task.scheduled_date.isoformat(),
                'created_at': new_task.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create maintenance task error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء مهمة الصيانة'}), 500

@maintenance_bp.route('/maintenance/<int:task_id>', methods=['GET'])
@token_required
def get_maintenance_task(current_user, task_id):
    """الحصول على مهمة صيانة معينة"""
    try:
        task_data = db.session.query(
            MaintenanceTask,
            Device.name.label('device_name'),
            Device.location.label('device_location'),
            Device.type.label('device_type'),
            User.name.label('assigned_user_name')
        ).join(Device).join(User).filter(MaintenanceTask.id == task_id).first()
        
        if not task_data:
            return jsonify({'message': 'مهمة الصيانة غير موجودة'}), 404
        
        task, device_name, device_location, device_type, assigned_user_name = task_data
        
        return jsonify({
            'task': {
                'id': task.id,
                'device_id': task.device_id,
                'device_name': device_name,
                'device_location': device_location,
                'device_type': device_type,
                'assigned_user_id': task.assigned_user_id,
                'assigned_user_name': assigned_user_name,
                'title': task.title,
                'description': task.description,
                'priority': task.priority,
                'status': task.status,
                'scheduled_date': task.scheduled_date.isoformat() if task.scheduled_date else None,
                'completed_date': task.completed_date.isoformat() if task.completed_date else None,
                'notes': task.notes,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'is_overdue': task.scheduled_date and task.scheduled_date < datetime.utcnow() and task.status == 'pending',
                'can_edit': task.assigned_user_id == current_user.id or current_user.can_manage_users()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get maintenance task error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب مهمة الصيانة'}), 500

@maintenance_bp.route('/maintenance/<int:task_id>', methods=['PUT'])
@token_required
def update_maintenance_task(current_user, task_id):
    """تحديث مهمة صيانة"""
    try:
        task = MaintenanceTask.query.get_or_404(task_id)
        
        # التحقق من الصلاحيات
        if task.assigned_user_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لتعديل هذه المهمة'}), 403
        
        data = request.get_json()
        
        # تحديث البيانات
        if 'title' in data:
            task.title = data['title']
        
        if 'description' in data:
            task.description = data['description']
        
        if 'priority' in data:
            task.priority = data['priority']
        
        if 'status' in data:
            old_status = task.status
            task.status = data['status']
            
            # إذا تم تغيير الحالة إلى مكتملة، تحديث تاريخ الإكمال
            if old_status != 'completed' and task.status == 'completed':
                task.completed_date = datetime.utcnow()
        
        if 'notes' in data:
            task.notes = data['notes']
        
        if 'scheduled_date' in data:
            try:
                task.scheduled_date = datetime.fromisoformat(
                    data['scheduled_date'].replace('Z', '+00:00')
                )
            except ValueError:
                pass
        
        if 'assigned_user_id' in data and current_user.can_manage_users():
            # التحقق من وجود المستخدم الجديد
            new_user = User.query.get(data['assigned_user_id'])
            if new_user:
                task.assigned_user_id = data['assigned_user_id']
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث مهمة الصيانة بنجاح',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'priority': task.priority,
                'status': task.status,
                'notes': task.notes,
                'scheduled_date': task.scheduled_date.isoformat() if task.scheduled_date else None,
                'completed_date': task.completed_date.isoformat() if task.completed_date else None,
                'updated_at': task.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update maintenance task error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تحديث مهمة الصيانة'}), 500

@maintenance_bp.route('/maintenance/<int:task_id>', methods=['DELETE'])
@token_required
def delete_maintenance_task(current_user, task_id):
    """حذف مهمة صيانة"""
    try:
        task = MaintenanceTask.query.get_or_404(task_id)
        
        # التحقق من الصلاحيات
        if not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لحذف مهام الصيانة'}), 403
        
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({'message': 'تم حذف مهمة الصيانة بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete maintenance task error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في حذف مهمة الصيانة'}), 500

@maintenance_bp.route('/maintenance/stats', methods=['GET'])
@token_required
def get_maintenance_stats(current_user):
    """الحصول على إحصائيات الصيانة"""
    try:
        # إحصائيات عامة
        total_tasks = MaintenanceTask.query.count()
        pending_tasks = MaintenanceTask.query.filter_by(status='pending').count()
        in_progress_tasks = MaintenanceTask.query.filter_by(status='in_progress').count()
        completed_tasks = MaintenanceTask.query.filter_by(status='completed').count()
        
        # المهام المتأخرة
        overdue_tasks = MaintenanceTask.query.filter(
            MaintenanceTask.status == 'pending',
            MaintenanceTask.scheduled_date < datetime.utcnow()
        ).count()
        
        # إحصائيات حسب الأولوية
        priority_stats = db.session.query(
            MaintenanceTask.priority,
            db.func.count(MaintenanceTask.id).label('count')
        ).filter(
            MaintenanceTask.status.in_(['pending', 'in_progress'])
        ).group_by(MaintenanceTask.priority).all()
        
        # إحصائيات حسب المستخدم
        user_stats = db.session.query(
            User.name,
            db.func.count(MaintenanceTask.id).label('total'),
            db.func.sum(db.case([(MaintenanceTask.status == 'completed', 1)], else_=0)).label('completed')
        ).join(MaintenanceTask).group_by(User.id, User.name).all()
        
        # إحصائيات الأسبوع الماضي
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_tasks = db.session.query(
            db.func.date(MaintenanceTask.created_at).label('date'),
            db.func.count(MaintenanceTask.id).label('count')
        ).filter(
            MaintenanceTask.created_at >= week_ago
        ).group_by(
            db.func.date(MaintenanceTask.created_at)
        ).order_by('date').all()
        
        # الأجهزة الأكثر صيانة
        device_stats = db.session.query(
            Device.name,
            Device.location,
            db.func.count(MaintenanceTask.id).label('count')
        ).join(MaintenanceTask).group_by(
            Device.id, Device.name, Device.location
        ).order_by(db.func.count(MaintenanceTask.id).desc()).limit(10).all()
        
        return jsonify({
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
            'priority_distribution': [
                {'priority': priority, 'count': count} for priority, count in priority_stats
            ],
            'user_performance': [
                {
                    'user': name,
                    'total_tasks': total,
                    'completed_tasks': completed or 0,
                    'completion_rate': round((completed or 0) / total * 100, 1) if total > 0 else 0
                } for name, total, completed in user_stats
            ],
            'weekly_trend': [
                {
                    'date': date.isoformat(),
                    'count': count
                } for date, count in weekly_tasks
            ],
            'top_devices': [
                {
                    'device_name': name,
                    'location': location,
                    'maintenance_count': count
                } for name, location, count in device_stats
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get maintenance stats error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب إحصائيات الصيانة'}), 500

@maintenance_bp.route('/maintenance/schedule', methods=['GET'])
@token_required
def get_maintenance_schedule(current_user):
    """الحصول على جدول الصيانة"""
    try:
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # تحديد نطاق التاريخ
        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                start = datetime.utcnow()
        else:
            start = datetime.utcnow()
        
        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                end = start + timedelta(days=30)
        else:
            end = start + timedelta(days=30)
        
        # جلب المهام في النطاق المحدد
        tasks = db.session.query(
            MaintenanceTask,
            Device.name.label('device_name'),
            Device.location.label('device_location'),
            User.name.label('assigned_user_name')
        ).join(Device).join(User).filter(
            MaintenanceTask.scheduled_date >= start,
            MaintenanceTask.scheduled_date <= end
        ).order_by(MaintenanceTask.scheduled_date.asc()).all()
        
        schedule_data = []
        for task, device_name, device_location, assigned_user_name in tasks:
            schedule_data.append({
                'id': task.id,
                'title': task.title,
                'device_name': device_name,
                'device_location': device_location,
                'assigned_user_name': assigned_user_name,
                'priority': task.priority,
                'status': task.status,
                'scheduled_date': task.scheduled_date.isoformat(),
                'is_overdue': task.scheduled_date < datetime.utcnow() and task.status == 'pending'
            })
        
        return jsonify({
            'schedule': schedule_data,
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'total_tasks': len(schedule_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get maintenance schedule error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب جدول الصيانة'}), 500

@maintenance_bp.route('/maintenance/templates', methods=['GET'])
@token_required
def get_maintenance_templates(current_user):
    """الحصول على قوالب الصيانة"""
    try:
        templates = [
            {
                'id': 'monthly_inspection',
                'name': 'تشييك شهري',
                'description': 'تشييك شهري شامل لجميع أجهزة السلامة',
                'priority': 'medium',
                'estimated_duration': 120,  # بالدقائق
                'checklist': [
                    'فحص مقياس الضغط',
                    'اختبار آلية التشغيل',
                    'فحص الخراطيم والوصلات',
                    'تنظيف الجهاز',
                    'فحص الملصقات والتعليمات'
                ]
            },
            {
                'id': 'quarterly_maintenance',
                'name': 'صيانة ربع سنوية',
                'description': 'صيانة دورية كل 3 أشهر',
                'priority': 'high',
                'estimated_duration': 180,
                'checklist': [
                    'فحص شامل للأجزاء الداخلية',
                    'استبدال القطع المستهلكة',
                    'معايرة الأجهزة',
                    'اختبار الأداء',
                    'تحديث السجلات'
                ]
            },
            {
                'id': 'annual_overhaul',
                'name': 'مراجعة سنوية',
                'description': 'مراجعة شاملة سنوية',
                'priority': 'high',
                'estimated_duration': 300,
                'checklist': [
                    'فحص شامل لجميع المكونات',
                    'استبدال الأجزاء حسب الحاجة',
                    'اختبار الأداء الكامل',
                    'تحديث الشهادات',
                    'إعداد تقرير مفصل'
                ]
            },
            {
                'id': 'emergency_repair',
                'name': 'إصلاح طارئ',
                'description': 'إصلاح عاجل للأعطال الطارئة',
                'priority': 'urgent',
                'estimated_duration': 60,
                'checklist': [
                    'تشخيص العطل',
                    'إصلاح المشكلة',
                    'اختبار التشغيل',
                    'توثيق الإصلاح'
                ]
            }
        ]
        
        return jsonify({
            'templates': templates,
            'message': 'تم جلب قوالب الصيانة بنجاح'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get maintenance templates error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب قوالب الصيانة'}), 500

@maintenance_bp.route('/maintenance/bulk-create', methods=['POST'])
@token_required
def bulk_create_maintenance_tasks(current_user):
    """إنشاء مهام صيانة متعددة"""
    try:
        data = request.get_json()
        tasks_data = data.get('tasks', [])
        template_id = data.get('template_id', '')
        
        if not tasks_data:
            return jsonify({'message': 'لم يتم تحديد أي مهام للإنشاء'}), 400
        
        created_tasks = []
        errors = []
        
        for task_data in tasks_data:
            try:
                device_id = task_data.get('device_id')
                assigned_user_id = task_data.get('assigned_user_id')
                title = task_data.get('title', '')
                scheduled_date = task_data.get('scheduled_date')
                
                if not device_id or not assigned_user_id or not title:
                    errors.append('معرف الجهاز والمستخدم المكلف والعنوان مطلوبة')
                    continue
                
                # التحقق من وجود الجهاز والمستخدم
                device = Device.query.get(device_id)
                user = User.query.get(assigned_user_id)
                
                if not device:
                    errors.append(f'الجهاز {device_id} غير موجود')
                    continue
                
                if not user:
                    errors.append(f'المستخدم {assigned_user_id} غير موجود')
                    continue
                
                # تحديد تاريخ الجدولة
                if scheduled_date:
                    try:
                        scheduled_datetime = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
                    except ValueError:
                        scheduled_datetime = datetime.utcnow() + timedelta(days=1)
                else:
                    scheduled_datetime = datetime.utcnow() + timedelta(days=1)
                
                # إنشاء المهمة
                new_task = MaintenanceTask(
                    device_id=device_id,
                    assigned_user_id=assigned_user_id,
                    title=title,
                    description=task_data.get('description', ''),
                    priority=task_data.get('priority', 'medium'),
                    scheduled_date=scheduled_datetime,
                    status='pending'
                )
                
                db.session.add(new_task)
                created_tasks.append({
                    'device_id': device_id,
                    'device_name': device.name,
                    'assigned_user_name': user.name,
                    'title': title,
                    'scheduled_date': scheduled_datetime.isoformat()
                })
                
            except Exception as e:
                errors.append(f'خطأ في إنشاء مهمة للجهاز {device_id}: {str(e)}')
        
        db.session.commit()
        
        return jsonify({
            'message': f'تم إنشاء {len(created_tasks)} مهمة صيانة بنجاح',
            'created_tasks': created_tasks,
            'errors': errors,
            'total_created': len(created_tasks),
            'total_errors': len(errors)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bulk create maintenance tasks error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في إنشاء مهام الصيانة'}), 500

