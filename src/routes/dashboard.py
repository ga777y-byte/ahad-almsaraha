from flask import Blueprint, jsonify, request, current_app
from src.models.user import User, Device, Inspection, MaintenanceTask, UploadedFile, db
from src.routes.auth import token_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_user):
    """الحصول على إحصائيات لوحة التحكم"""
    try:
        # الإحصائيات الأساسية
        total_devices = Device.query.filter_by(status='active').count()
        total_users = User.query.filter_by(is_active=True).count()
        
        # تشييكات اليوم
        today = datetime.utcnow().date()
        today_inspections = Inspection.query.filter(
            func.date(Inspection.inspection_date) == today
        ).count()
        
        # مهام الصيانة المعلقة
        pending_maintenance = MaintenanceTask.query.filter(
            MaintenanceTask.status.in_(['pending', 'in_progress'])
        ).count()
        
        # مهام الصيانة المتأخرة
        overdue_maintenance = MaintenanceTask.query.filter(
            and_(
                MaintenanceTask.status == 'pending',
                MaintenanceTask.scheduled_date < datetime.utcnow()
            )
        ).count()
        
        # الملفات المرفوعة
        total_files = UploadedFile.query.count()
        
        # إحصائيات الأجهزة حسب النوع
        device_types = db.session.query(
            Device.type,
            func.count(Device.id).label('count')
        ).filter_by(status='active').group_by(Device.type).all()
        
        # إحصائيات التشييكات الأخيرة
        recent_inspections = db.session.query(
            Inspection.status,
            func.count(Inspection.id).label('count')
        ).filter(
            Inspection.inspection_date >= datetime.utcnow() - timedelta(days=7)
        ).group_by(Inspection.status).all()
        
        # إحصائيات مهام الصيانة حسب الحالة
        maintenance_stats = db.session.query(
            MaintenanceTask.status,
            func.count(MaintenanceTask.id).label('count')
        ).group_by(MaintenanceTask.status).all()
        
        # إحصائيات مهام الصيانة حسب الأولوية
        priority_stats = db.session.query(
            MaintenanceTask.priority,
            func.count(MaintenanceTask.id).label('count')
        ).filter(
            MaintenanceTask.status.in_(['pending', 'in_progress'])
        ).group_by(MaintenanceTask.priority).all()
        
        # الأجهزة التي تحتاج صيانة قريباً (خلال 30 يوم)
        upcoming_maintenance = Device.query.filter(
            and_(
                Device.next_maintenance.isnot(None),
                Device.next_maintenance <= datetime.utcnow().date() + timedelta(days=30),
                Device.status == 'active'
            )
        ).count()
        
        # آخر التشييكات
        latest_inspections = db.session.query(
            Inspection,
            Device.name.label('device_name'),
            User.name.label('inspector_name')
        ).join(Device).join(User).order_by(
            Inspection.inspection_date.desc()
        ).limit(5).all()
        
        # مهام الصيانة العاجلة
        urgent_tasks = db.session.query(
            MaintenanceTask,
            Device.name.label('device_name'),
            User.name.label('assigned_user_name')
        ).join(Device).join(User).filter(
            and_(
                MaintenanceTask.priority == 'urgent',
                MaintenanceTask.status.in_(['pending', 'in_progress'])
            )
        ).order_by(MaintenanceTask.scheduled_date.asc()).limit(5).all()
        
        return jsonify({
            'basic_stats': {
                'totalDevices': total_devices,
                'todayInspections': today_inspections,
                'pendingMaintenance': pending_maintenance,
                'totalUsers': total_users,
                'overdueMaintenance': overdue_maintenance,
                'totalFiles': total_files,
                'upcomingMaintenance': upcoming_maintenance
            },
            'device_types': [
                {'type': dtype, 'count': count} for dtype, count in device_types
            ],
            'inspection_stats': [
                {'status': status, 'count': count} for status, count in recent_inspections
            ],
            'maintenance_stats': [
                {'status': status, 'count': count} for status, count in maintenance_stats
            ],
            'priority_stats': [
                {'priority': priority, 'count': count} for priority, count in priority_stats
            ],
            'latest_inspections': [
                {
                    'id': inspection.id,
                    'device_name': device_name,
                    'inspector_name': inspector_name,
                    'status': inspection.status,
                    'inspection_date': inspection.inspection_date.isoformat(),
                    'notes': inspection.notes[:100] + '...' if inspection.notes and len(inspection.notes) > 100 else inspection.notes
                }
                for inspection, device_name, inspector_name in latest_inspections
            ],
            'urgent_tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'device_name': device_name,
                    'assigned_user_name': assigned_user_name,
                    'priority': task.priority,
                    'status': task.status,
                    'scheduled_date': task.scheduled_date.isoformat() if task.scheduled_date else None
                }
                for task, device_name, assigned_user_name in urgent_tasks
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get dashboard stats error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب إحصائيات لوحة التحكم'}), 500

@dashboard_bp.route('/activity', methods=['GET'])
@token_required
def get_recent_activity(current_user):
    """الحصول على النشاطات الأخيرة"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        activities = []
        
        # آخر التشييكات
        recent_inspections = db.session.query(
            Inspection,
            Device.name.label('device_name'),
            User.name.label('inspector_name')
        ).join(Device).join(User).order_by(
            Inspection.inspection_date.desc()
        ).limit(limit // 2).all()
        
        for inspection, device_name, inspector_name in recent_inspections:
            activities.append({
                'type': 'inspection',
                'title': f'تشييك {device_name}',
                'description': f'تم إجراء تشييك بواسطة {inspector_name}',
                'status': inspection.status,
                'timestamp': inspection.inspection_date.isoformat(),
                'user': inspector_name,
                'icon': '🔍'
            })
        
        # آخر مهام الصيانة
        recent_maintenance = db.session.query(
            MaintenanceTask,
            Device.name.label('device_name'),
            User.name.label('assigned_user_name')
        ).join(Device).join(User).order_by(
            MaintenanceTask.updated_at.desc()
        ).limit(limit // 2).all()
        
        for task, device_name, assigned_user_name in recent_maintenance:
            activities.append({
                'type': 'maintenance',
                'title': task.title,
                'description': f'مهمة صيانة لـ {device_name} - {assigned_user_name}',
                'status': task.status,
                'timestamp': task.updated_at.isoformat(),
                'user': assigned_user_name,
                'priority': task.priority,
                'icon': '⚙️'
            })
        
        # ترتيب النشاطات حسب الوقت
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'activities': activities[:limit]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get recent activity error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب النشاطات الأخيرة'}), 500

@dashboard_bp.route('/charts/inspections', methods=['GET'])
@token_required
def get_inspections_chart_data(current_user):
    """الحصول على بيانات مخطط التشييكات"""
    try:
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # بيانات التشييكات اليومية
        daily_inspections = db.session.query(
            func.date(Inspection.inspection_date).label('date'),
            func.count(Inspection.id).label('count')
        ).filter(
            Inspection.inspection_date >= start_date
        ).group_by(
            func.date(Inspection.inspection_date)
        ).order_by('date').all()
        
        # بيانات التشييكات حسب الحالة
        status_data = db.session.query(
            Inspection.status,
            func.count(Inspection.id).label('count')
        ).filter(
            Inspection.inspection_date >= start_date
        ).group_by(Inspection.status).all()
        
        return jsonify({
            'daily_inspections': [
                {
                    'date': date.isoformat(),
                    'count': count
                }
                for date, count in daily_inspections
            ],
            'status_distribution': [
                {
                    'status': status,
                    'count': count
                }
                for status, count in status_data
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get inspections chart data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب بيانات مخطط التشييكات'}), 500

@dashboard_bp.route('/charts/maintenance', methods=['GET'])
@token_required
def get_maintenance_chart_data(current_user):
    """الحصول على بيانات مخطط الصيانة"""
    try:
        # بيانات الصيانة حسب الحالة
        status_data = db.session.query(
            MaintenanceTask.status,
            func.count(MaintenanceTask.id).label('count')
        ).group_by(MaintenanceTask.status).all()
        
        # بيانات الصيانة حسب الأولوية
        priority_data = db.session.query(
            MaintenanceTask.priority,
            func.count(MaintenanceTask.id).label('count')
        ).group_by(MaintenanceTask.priority).all()
        
        # بيانات الصيانة الشهرية
        monthly_data = db.session.query(
            func.extract('year', MaintenanceTask.created_at).label('year'),
            func.extract('month', MaintenanceTask.created_at).label('month'),
            func.count(MaintenanceTask.id).label('count')
        ).filter(
            MaintenanceTask.created_at >= datetime.utcnow() - timedelta(days=365)
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        return jsonify({
            'status_distribution': [
                {
                    'status': status,
                    'count': count
                }
                for status, count in status_data
            ],
            'priority_distribution': [
                {
                    'priority': priority,
                    'count': count
                }
                for priority, count in priority_data
            ],
            'monthly_trends': [
                {
                    'year': int(year),
                    'month': int(month),
                    'count': count
                }
                for year, month, count in monthly_data
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get maintenance chart data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب بيانات مخطط الصيانة'}), 500

@dashboard_bp.route('/alerts', methods=['GET'])
@token_required
def get_system_alerts(current_user):
    """الحصول على تنبيهات النظام"""
    try:
        alerts = []
        
        # تنبيهات الصيانة المتأخرة
        overdue_tasks = db.session.query(
            MaintenanceTask,
            Device.name.label('device_name')
        ).join(Device).filter(
            and_(
                MaintenanceTask.status == 'pending',
                MaintenanceTask.scheduled_date < datetime.utcnow()
            )
        ).all()
        
        for task, device_name in overdue_tasks:
            days_overdue = (datetime.utcnow() - task.scheduled_date).days
            alerts.append({
                'type': 'overdue_maintenance',
                'severity': 'high' if days_overdue > 7 else 'medium',
                'title': 'صيانة متأخرة',
                'message': f'مهمة صيانة {task.title} لجهاز {device_name} متأخرة بـ {days_overdue} يوم',
                'timestamp': task.scheduled_date.isoformat(),
                'action_url': f'/maintenance.html?task_id={task.id}'
            })
        
        # تنبيهات الأجهزة التي تحتاج صيانة قريباً
        upcoming_maintenance = db.session.query(Device).filter(
            and_(
                Device.next_maintenance.isnot(None),
                Device.next_maintenance <= datetime.utcnow().date() + timedelta(days=7),
                Device.next_maintenance > datetime.utcnow().date(),
                Device.status == 'active'
            )
        ).all()
        
        for device in upcoming_maintenance:
            days_until = (device.next_maintenance - datetime.utcnow().date()).days
            alerts.append({
                'type': 'upcoming_maintenance',
                'severity': 'low' if days_until > 3 else 'medium',
                'title': 'صيانة قادمة',
                'message': f'جهاز {device.name} يحتاج صيانة خلال {days_until} يوم',
                'timestamp': device.next_maintenance.isoformat(),
                'action_url': f'/devices.html?device_id={device.id}'
            })
        
        # تنبيهات التشييكات الخطيرة
        danger_inspections = db.session.query(
            Inspection,
            Device.name.label('device_name')
        ).join(Device).filter(
            and_(
                Inspection.status == 'danger',
                Inspection.inspection_date >= datetime.utcnow() - timedelta(days=1)
            )
        ).all()
        
        for inspection, device_name in danger_inspections:
            alerts.append({
                'type': 'danger_inspection',
                'severity': 'critical',
                'title': 'تشييك خطير',
                'message': f'تم العثور على مشكلة خطيرة في جهاز {device_name}',
                'timestamp': inspection.inspection_date.isoformat(),
                'action_url': f'/inspections.html?inspection_id={inspection.id}'
            })
        
        # ترتيب التنبيهات حسب الأهمية والوقت
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: (severity_order.get(x['severity'], 4), x['timestamp']), reverse=True)
        
        return jsonify({
            'alerts': alerts,
            'total_count': len(alerts),
            'critical_count': len([a for a in alerts if a['severity'] == 'critical']),
            'high_count': len([a for a in alerts if a['severity'] == 'high']),
            'medium_count': len([a for a in alerts if a['severity'] == 'medium']),
            'low_count': len([a for a in alerts if a['severity'] == 'low'])
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get system alerts error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب تنبيهات النظام'}), 500

@dashboard_bp.route('/summary', methods=['GET'])
@token_required
def get_dashboard_summary(current_user):
    """الحصول على ملخص لوحة التحكم"""
    try:
        # ملخص سريع للمستخدم الحالي
        user_inspections = Inspection.query.filter_by(inspector_id=current_user.id).count()
        user_tasks = MaintenanceTask.query.filter_by(assigned_user_id=current_user.id).count()
        
        # ملخص النظام العام
        system_health = {
            'devices_operational': Device.query.filter_by(status='active').count(),
            'recent_inspections_good': Inspection.query.filter(
                and_(
                    Inspection.status == 'good',
                    Inspection.inspection_date >= datetime.utcnow() - timedelta(days=7)
                )
            ).count(),
            'maintenance_on_schedule': MaintenanceTask.query.filter(
                and_(
                    MaintenanceTask.status == 'completed',
                    MaintenanceTask.completed_date >= MaintenanceTask.scheduled_date
                )
            ).count()
        }
        
        # اتجاهات الأداء
        current_week_inspections = Inspection.query.filter(
            Inspection.inspection_date >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        previous_week_inspections = Inspection.query.filter(
            and_(
                Inspection.inspection_date >= datetime.utcnow() - timedelta(days=14),
                Inspection.inspection_date < datetime.utcnow() - timedelta(days=7)
            )
        ).count()
        
        inspection_trend = 'up' if current_week_inspections > previous_week_inspections else 'down' if current_week_inspections < previous_week_inspections else 'stable'
        
        return jsonify({
            'user_summary': {
                'total_inspections': user_inspections,
                'assigned_tasks': user_tasks,
                'role': current_user.role,
                'department': current_user.department
            },
            'system_health': system_health,
            'trends': {
                'inspections': {
                    'current_week': current_week_inspections,
                    'previous_week': previous_week_inspections,
                    'trend': inspection_trend
                }
            },
            'quick_actions': [
                {'title': 'إجراء تشييك جديد', 'url': '/inspections.html', 'icon': '🔍'},
                {'title': 'إضافة مهمة صيانة', 'url': '/maintenance.html', 'icon': '⚙️'},
                {'title': 'رفع ملف جديد', 'url': '/library.html', 'icon': '📁'},
                {'title': 'عرض التقارير', 'url': '/reports.html', 'icon': '📊'}
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get dashboard summary error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب ملخص لوحة التحكم'}), 500

