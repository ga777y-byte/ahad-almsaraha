from flask import Blueprint, jsonify, request, current_app
from src.models.user import AutoSaveData, db
from src.routes.auth import token_required
from datetime import datetime
import json

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/save', methods=['POST'])
@token_required
def save_data(current_user):
    """حفظ البيانات للمزامنة"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'البيانات مطلوبة'}), 400
        
        page_path = data.get('page', request.referrer or '/')
        save_data = data.get('data', {})
        timestamp = data.get('timestamp', datetime.utcnow().timestamp())
        
        # البحث عن بيانات موجودة للصفحة والمستخدم
        existing_data = AutoSaveData.query.filter_by(
            user_id=current_user.id,
            page_path=page_path
        ).first()
        
        if existing_data:
            # تحديث البيانات الموجودة
            existing_data.data = json.dumps(save_data, ensure_ascii=False)
            existing_data.timestamp = datetime.fromtimestamp(timestamp)
        else:
            # إنشاء بيانات جديدة
            new_data = AutoSaveData(
                user_id=current_user.id,
                page_path=page_path,
                data=json.dumps(save_data, ensure_ascii=False),
                timestamp=datetime.fromtimestamp(timestamp)
            )
            db.session.add(new_data)
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم حفظ البيانات بنجاح',
            'timestamp': timestamp
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Save data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في حفظ البيانات'}), 500

@sync_bp.route('/restore', methods=['GET'])
@token_required
def restore_data(current_user):
    """استعادة البيانات المحفوظة"""
    try:
        page_path = request.args.get('page', '/')
        
        # البحث عن البيانات المحفوظة
        saved_data = AutoSaveData.query.filter_by(
            user_id=current_user.id,
            page_path=page_path
        ).order_by(AutoSaveData.timestamp.desc()).first()
        
        if saved_data:
            try:
                data = json.loads(saved_data.data)
                return jsonify({
                    'data': data,
                    'timestamp': saved_data.timestamp.timestamp(),
                    'page_path': saved_data.page_path
                }), 200
            except json.JSONDecodeError:
                return jsonify({
                    'data': {},
                    'message': 'خطأ في تحليل البيانات المحفوظة'
                }), 200
        else:
            return jsonify({
                'data': {},
                'message': 'لا توجد بيانات محفوظة'
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Restore data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في استعادة البيانات'}), 500

@sync_bp.route('/sync-all', methods=['GET'])
@token_required
def sync_all_data(current_user):
    """مزامنة جميع البيانات المحفوظة للمستخدم"""
    try:
        # الحصول على جميع البيانات المحفوظة للمستخدم
        all_data = AutoSaveData.query.filter_by(
            user_id=current_user.id
        ).order_by(AutoSaveData.timestamp.desc()).all()
        
        sync_data = {}
        for item in all_data:
            try:
                data = json.loads(item.data)
                sync_data[item.page_path] = {
                    'data': data,
                    'timestamp': item.timestamp.timestamp()
                }
            except json.JSONDecodeError:
                continue
        
        return jsonify({
            'sync_data': sync_data,
            'total_pages': len(sync_data),
            'last_sync': datetime.utcnow().timestamp()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Sync all data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في مزامنة البيانات'}), 500

@sync_bp.route('/clear', methods=['POST'])
@token_required
def clear_saved_data(current_user):
    """مسح البيانات المحفوظة"""
    try:
        data = request.get_json()
        page_path = data.get('page') if data else None
        
        if page_path:
            # مسح بيانات صفحة معينة
            AutoSaveData.query.filter_by(
                user_id=current_user.id,
                page_path=page_path
            ).delete()
            message = f'تم مسح البيانات المحفوظة للصفحة {page_path}'
        else:
            # مسح جميع البيانات المحفوظة للمستخدم
            AutoSaveData.query.filter_by(user_id=current_user.id).delete()
            message = 'تم مسح جميع البيانات المحفوظة'
        
        db.session.commit()
        
        return jsonify({'message': message}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Clear saved data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في مسح البيانات'}), 500

@sync_bp.route('/export', methods=['GET'])
@token_required
def export_data(current_user):
    """تصدير البيانات المحفوظة"""
    try:
        # الحصول على جميع البيانات المحفوظة للمستخدم
        all_data = AutoSaveData.query.filter_by(
            user_id=current_user.id
        ).order_by(AutoSaveData.timestamp.desc()).all()
        
        export_data = {
            'user_id': current_user.id,
            'user_email': current_user.email,
            'user_name': current_user.name,
            'export_timestamp': datetime.utcnow().isoformat(),
            'data': []
        }
        
        for item in all_data:
            try:
                data = json.loads(item.data)
                export_data['data'].append({
                    'page_path': item.page_path,
                    'data': data,
                    'timestamp': item.timestamp.isoformat()
                })
            except json.JSONDecodeError:
                continue
        
        return jsonify(export_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Export data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تصدير البيانات'}), 500

@sync_bp.route('/import', methods=['POST'])
@token_required
def import_data(current_user):
    """استيراد البيانات المحفوظة"""
    try:
        data = request.get_json()
        
        if not data or 'data' not in data:
            return jsonify({'message': 'بيانات الاستيراد مطلوبة'}), 400
        
        import_data = data['data']
        imported_count = 0
        
        for item in import_data:
            page_path = item.get('page_path')
            item_data = item.get('data')
            timestamp_str = item.get('timestamp')
            
            if not page_path or not item_data:
                continue
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
            
            # البحث عن بيانات موجودة
            existing_data = AutoSaveData.query.filter_by(
                user_id=current_user.id,
                page_path=page_path
            ).first()
            
            if existing_data:
                # تحديث إذا كانت البيانات المستوردة أحدث
                if timestamp > existing_data.timestamp:
                    existing_data.data = json.dumps(item_data, ensure_ascii=False)
                    existing_data.timestamp = timestamp
                    imported_count += 1
            else:
                # إنشاء بيانات جديدة
                new_data = AutoSaveData(
                    user_id=current_user.id,
                    page_path=page_path,
                    data=json.dumps(item_data, ensure_ascii=False),
                    timestamp=timestamp
                )
                db.session.add(new_data)
                imported_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'تم استيراد {imported_count} عنصر بنجاح',
            'imported_count': imported_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Import data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في استيراد البيانات'}), 500

@sync_bp.route('/stats', methods=['GET'])
@token_required
def get_sync_stats(current_user):
    """الحصول على إحصائيات المزامنة"""
    try:
        # إحصائيات المستخدم الحالي
        user_data_count = AutoSaveData.query.filter_by(user_id=current_user.id).count()
        
        # آخر وقت حفظ
        last_save = AutoSaveData.query.filter_by(
            user_id=current_user.id
        ).order_by(AutoSaveData.timestamp.desc()).first()
        
        # الصفحات المحفوظة
        pages_query = db.session.query(AutoSaveData.page_path).filter_by(
            user_id=current_user.id
        ).distinct().all()
        
        saved_pages = [page[0] for page in pages_query]
        
        # إحصائيات عامة (للمدير فقط)
        general_stats = {}
        if current_user.can_manage_users():
            total_saved_data = AutoSaveData.query.count()
            total_users_with_data = db.session.query(AutoSaveData.user_id).distinct().count()
            
            general_stats = {
                'total_saved_data': total_saved_data,
                'total_users_with_data': total_users_with_data
            }
        
        return jsonify({
            'user_stats': {
                'saved_data_count': user_data_count,
                'saved_pages_count': len(saved_pages),
                'saved_pages': saved_pages,
                'last_save_time': last_save.timestamp.isoformat() if last_save else None
            },
            'general_stats': general_stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get sync stats error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب إحصائيات المزامنة'}), 500

@sync_bp.route('/cleanup', methods=['POST'])
@token_required
def cleanup_old_data(current_user):
    """تنظيف البيانات القديمة"""
    try:
        data = request.get_json()
        days_old = data.get('days_old', 30) if data else 30
        
        # حساب التاريخ المحدد
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        if current_user.can_manage_users():
            # المدير يمكنه تنظيف جميع البيانات القديمة
            deleted_count = AutoSaveData.query.filter(
                AutoSaveData.timestamp < cutoff_date
            ).delete()
        else:
            # المستخدم العادي يمكنه تنظيف بياناته فقط
            deleted_count = AutoSaveData.query.filter(
                AutoSaveData.user_id == current_user.id,
                AutoSaveData.timestamp < cutoff_date
            ).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': f'تم حذف {deleted_count} عنصر أقدم من {days_old} يوم',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cleanup old data error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تنظيف البيانات القديمة'}), 500

