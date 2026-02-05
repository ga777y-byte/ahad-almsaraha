from flask import Blueprint, jsonify, request, current_app, send_file, send_from_directory
from werkzeug.utils import secure_filename
from src.models.user import UploadedFile, db
from src.routes.auth import token_required
import os
import uuid
from datetime import datetime
import mimetypes
from PIL import Image
import zipfile
import tempfile

files_bp = Blueprint('files', __name__)

# إعدادات رفع الملفات
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {
    'images': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'},
    'documents': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'odt', 'ods', 'odp'},
    'archives': {'zip', 'rar', '7z', 'tar', 'gz'},
    'videos': {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'},
    'audio': {'mp3', 'wav', 'ogg', 'aac', 'm4a'}
}

ALL_ALLOWED_EXTENSIONS = set()
for extensions in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(extensions)

def allowed_file(filename):
    """التحقق من نوع الملف المسموح"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALL_ALLOWED_EXTENSIONS

def get_file_category(filename):
    """تحديد فئة الملف"""
    if not filename:
        return 'other'
    
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    for category, extensions in ALLOWED_EXTENSIONS.items():
        if extension in extensions:
            return category
    
    return 'other'

def get_unique_filename(filename):
    """إنشاء اسم ملف فريد"""
    name, ext = os.path.splitext(secure_filename(filename))
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{name}_{timestamp}_{unique_id}{ext}"

def create_thumbnail(file_path, thumbnail_path, size=(200, 200)):
    """إنشاء صورة مصغرة للصور"""
    try:
        with Image.open(file_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, optimize=True, quality=85)
            return True
    except Exception as e:
        current_app.logger.error(f"Error creating thumbnail: {str(e)}")
        return False

@files_bp.route('/upload', methods=['POST'])
@token_required
def upload_files(current_user):
    """رفع الملفات"""
    try:
        if 'files' not in request.files:
            return jsonify({'message': 'لم يتم اختيار أي ملفات'}), 400
        
        files = request.files.getlist('files')
        category = request.form.get('category', 'general')
        description = request.form.get('description', '')
        is_public = request.form.get('is_public', 'false').lower() == 'true'
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'message': 'لم يتم اختيار أي ملفات'}), 400
        
        uploaded_files = []
        errors = []
        
        # إنشاء مجلد التحميل إذا لم يكن موجود
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        for file in files:
            if file.filename == '':
                continue
            
            # التحقق من نوع الملف
            if not allowed_file(file.filename):
                errors.append(f'نوع الملف {file.filename} غير مسموح')
                continue
            
            # التحقق من حجم الملف
            file.seek(0, 2)  # الانتقال إلى نهاية الملف
            file_size = file.tell()
            file.seek(0)  # العودة إلى بداية الملف
            
            if file_size > MAX_FILE_SIZE:
                errors.append(f'حجم الملف {file.filename} كبير جداً (الحد الأقصى {MAX_FILE_SIZE // (1024*1024)} MB)')
                continue
            
            # إنشاء اسم ملف فريد
            unique_filename = get_unique_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            try:
                # حفظ الملف
                file.save(file_path)
                
                # إنشاء صورة مصغرة للصور
                thumbnail_path = None
                if get_file_category(file.filename) == 'images':
                    thumbnail_filename = f"thumb_{unique_filename}"
                    thumbnail_path = os.path.join(UPLOAD_FOLDER, thumbnail_filename)
                    create_thumbnail(file_path, thumbnail_path)
                
                # حفظ معلومات الملف في قاعدة البيانات
                uploaded_file = UploadedFile(
                    uploader_id=current_user.id,
                    filename=unique_filename,
                    original_filename=file.filename,
                    file_type=get_file_category(file.filename),
                    file_size=file_size,
                    file_path=file_path,
                    category=category,
                    description=description,
                    is_public=is_public
                )
                
                db.session.add(uploaded_file)
                db.session.commit()
                
                uploaded_files.append({
                    'id': uploaded_file.id,
                    'filename': uploaded_file.filename,
                    'original_filename': uploaded_file.original_filename,
                    'file_type': uploaded_file.file_type,
                    'file_size': uploaded_file.file_size,
                    'category': uploaded_file.category,
                    'description': uploaded_file.description,
                    'is_public': uploaded_file.is_public,
                    'upload_date': uploaded_file.upload_date.isoformat(),
                    'download_url': f'/api/files/{uploaded_file.id}/download',
                    'thumbnail_url': f'/api/files/{uploaded_file.id}/thumbnail' if thumbnail_path else None
                })
                
            except Exception as e:
                errors.append(f'خطأ في حفظ الملف {file.filename}: {str(e)}')
                # حذف الملف إذا فشل حفظ البيانات
                if os.path.exists(file_path):
                    os.remove(file_path)
                continue
        
        response_data = {
            'message': f'تم رفع {len(uploaded_files)} ملف بنجاح',
            'uploaded_files': uploaded_files,
            'total_uploaded': len(uploaded_files),
            'total_errors': len(errors)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return jsonify(response_data), 200 if uploaded_files else 400
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Upload files error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في رفع الملفات'}), 500

@files_bp.route('/files', methods=['GET'])
@token_required
def get_files(current_user):
    """الحصول على قائمة الملفات"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category', '')
        file_type = request.args.get('file_type', '')
        search = request.args.get('search', '')
        my_files_only = request.args.get('my_files_only', 'false').lower() == 'true'
        
        # بناء الاستعلام
        query = UploadedFile.query
        
        # تصفية حسب المستخدم
        if my_files_only:
            query = query.filter(UploadedFile.uploader_id == current_user.id)
        else:
            # إظهار الملفات العامة أو ملفات المستخدم
            query = query.filter(
                (UploadedFile.is_public == True) | 
                (UploadedFile.uploader_id == current_user.id)
            )
        
        # تصفية حسب الفئة
        if category:
            query = query.filter(UploadedFile.category == category)
        
        # تصفية حسب نوع الملف
        if file_type:
            query = query.filter(UploadedFile.file_type == file_type)
        
        # البحث
        if search:
            query = query.filter(
                (UploadedFile.original_filename.contains(search)) |
                (UploadedFile.description.contains(search))
            )
        
        # ترتيب النتائج
        query = query.order_by(UploadedFile.upload_date.desc())
        
        # تطبيق التصفح
        files = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        files_data = []
        for file in files.items:
            file_data = {
                'id': file.id,
                'filename': file.filename,
                'original_filename': file.original_filename,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'file_size_formatted': format_file_size(file.file_size),
                'category': file.category,
                'description': file.description,
                'is_public': file.is_public,
                'upload_date': file.upload_date.isoformat(),
                'uploader_name': file.uploader.name,
                'download_url': f'/api/files/{file.id}/download',
                'can_delete': file.uploader_id == current_user.id or current_user.can_manage_users()
            }
            
            # إضافة رابط الصورة المصغرة للصور
            if file.file_type == 'images':
                file_data['thumbnail_url'] = f'/api/files/{file.id}/thumbnail'
                file_data['preview_url'] = f'/api/files/{file.id}/preview'
            
            files_data.append(file_data)
        
        return jsonify({
            'files': files_data,
            'pagination': {
                'page': page,
                'pages': files.pages,
                'per_page': per_page,
                'total': files.total,
                'has_next': files.has_next,
                'has_prev': files.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get files error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الملفات'}), 500

@files_bp.route('/files/<int:file_id>', methods=['GET'])
@token_required
def get_file_info(current_user, file_id):
    """الحصول على معلومات ملف معين"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # التحقق من الصلاحيات
        if not file.is_public and file.uploader_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لعرض هذا الملف'}), 403
        
        return jsonify({
            'id': file.id,
            'filename': file.filename,
            'original_filename': file.original_filename,
            'file_type': file.file_type,
            'file_size': file.file_size,
            'file_size_formatted': format_file_size(file.file_size),
            'category': file.category,
            'description': file.description,
            'is_public': file.is_public,
            'upload_date': file.upload_date.isoformat(),
            'uploader_name': file.uploader.name,
            'uploader_email': file.uploader.email,
            'download_url': f'/api/files/{file.id}/download',
            'can_delete': file.uploader_id == current_user.id or current_user.can_manage_users(),
            'can_edit': file.uploader_id == current_user.id or current_user.can_manage_users()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get file info error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب معلومات الملف'}), 500

@files_bp.route('/files/<int:file_id>/download', methods=['GET'])
@token_required
def download_file(current_user, file_id):
    """تحميل ملف"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # التحقق من الصلاحيات
        if not file.is_public and file.uploader_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لتحميل هذا الملف'}), 403
        
        # التحقق من وجود الملف
        if not os.path.exists(file.file_path):
            return jsonify({'message': 'الملف غير موجود على الخادم'}), 404
        
        return send_file(
            file.file_path,
            as_attachment=True,
            download_name=file.original_filename,
            mimetype=mimetypes.guess_type(file.original_filename)[0]
        )
        
    except Exception as e:
        current_app.logger.error(f"Download file error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تحميل الملف'}), 500

@files_bp.route('/files/<int:file_id>/preview', methods=['GET'])
@token_required
def preview_file(current_user, file_id):
    """معاينة ملف (للصور فقط)"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # التحقق من الصلاحيات
        if not file.is_public and file.uploader_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لمعاينة هذا الملف'}), 403
        
        # التحقق من نوع الملف
        if file.file_type != 'images':
            return jsonify({'message': 'المعاينة متاحة للصور فقط'}), 400
        
        # التحقق من وجود الملف
        if not os.path.exists(file.file_path):
            return jsonify({'message': 'الملف غير موجود على الخادم'}), 404
        
        return send_file(
            file.file_path,
            mimetype=mimetypes.guess_type(file.original_filename)[0]
        )
        
    except Exception as e:
        current_app.logger.error(f"Preview file error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في معاينة الملف'}), 500

@files_bp.route('/files/<int:file_id>/thumbnail', methods=['GET'])
@token_required
def get_thumbnail(current_user, file_id):
    """الحصول على الصورة المصغرة"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # التحقق من الصلاحيات
        if not file.is_public and file.uploader_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لعرض هذا الملف'}), 403
        
        # التحقق من نوع الملف
        if file.file_type != 'images':
            return jsonify({'message': 'الصور المصغرة متاحة للصور فقط'}), 400
        
        # البحث عن الصورة المصغرة
        thumbnail_filename = f"thumb_{file.filename}"
        thumbnail_path = os.path.join(UPLOAD_FOLDER, thumbnail_filename)
        
        if os.path.exists(thumbnail_path):
            return send_file(thumbnail_path, mimetype='image/jpeg')
        else:
            # إنشاء صورة مصغرة إذا لم تكن موجودة
            if os.path.exists(file.file_path):
                if create_thumbnail(file.file_path, thumbnail_path):
                    return send_file(thumbnail_path, mimetype='image/jpeg')
            
            # إرجاع الصورة الأصلية إذا فشل إنشاء المصغرة
            return send_file(file.file_path, mimetype=mimetypes.guess_type(file.original_filename)[0])
        
    except Exception as e:
        current_app.logger.error(f"Get thumbnail error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب الصورة المصغرة'}), 500

@files_bp.route('/files/<int:file_id>', methods=['PUT'])
@token_required
def update_file(current_user, file_id):
    """تحديث معلومات ملف"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # التحقق من الصلاحيات
        if file.uploader_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لتعديل هذا الملف'}), 403
        
        data = request.get_json()
        
        if 'description' in data:
            file.description = data['description']
        
        if 'category' in data:
            file.category = data['category']
        
        if 'is_public' in data:
            file.is_public = data['is_public']
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث الملف بنجاح',
            'file': {
                'id': file.id,
                'description': file.description,
                'category': file.category,
                'is_public': file.is_public
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update file error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في تحديث الملف'}), 500

@files_bp.route('/files/<int:file_id>', methods=['DELETE'])
@token_required
def delete_file(current_user, file_id):
    """حذف ملف"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        # التحقق من الصلاحيات
        if file.uploader_id != current_user.id and not current_user.can_manage_users():
            return jsonify({'message': 'ليس لديك صلاحية لحذف هذا الملف'}), 403
        
        # حذف الملف من النظام
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        
        # حذف الصورة المصغرة إن وجدت
        if file.file_type == 'images':
            thumbnail_filename = f"thumb_{file.filename}"
            thumbnail_path = os.path.join(UPLOAD_FOLDER, thumbnail_filename)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
        
        # حذف السجل من قاعدة البيانات
        db.session.delete(file)
        db.session.commit()
        
        return jsonify({'message': 'تم حذف الملف بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete file error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في حذف الملف'}), 500

@files_bp.route('/files/bulk-delete', methods=['POST'])
@token_required
def bulk_delete_files(current_user):
    """حذف متعدد للملفات"""
    try:
        data = request.get_json()
        file_ids = data.get('file_ids', [])
        
        if not file_ids:
            return jsonify({'message': 'لم يتم تحديد أي ملفات للحذف'}), 400
        
        deleted_count = 0
        errors = []
        
        for file_id in file_ids:
            try:
                file = UploadedFile.query.get(file_id)
                if not file:
                    errors.append(f'الملف {file_id} غير موجود')
                    continue
                
                # التحقق من الصلاحيات
                if file.uploader_id != current_user.id and not current_user.can_manage_users():
                    errors.append(f'ليس لديك صلاحية لحذف الملف {file.original_filename}')
                    continue
                
                # حذف الملف من النظام
                if os.path.exists(file.file_path):
                    os.remove(file.file_path)
                
                # حذف الصورة المصغرة إن وجدت
                if file.file_type == 'images':
                    thumbnail_filename = f"thumb_{file.filename}"
                    thumbnail_path = os.path.join(UPLOAD_FOLDER, thumbnail_filename)
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                
                # حذف السجل من قاعدة البيانات
                db.session.delete(file)
                deleted_count += 1
                
            except Exception as e:
                errors.append(f'خطأ في حذف الملف {file_id}: {str(e)}')
        
        db.session.commit()
        
        response_data = {
            'message': f'تم حذف {deleted_count} ملف بنجاح',
            'deleted_count': deleted_count,
            'total_requested': len(file_ids)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bulk delete files error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في حذف الملفات'}), 500

@files_bp.route('/files/stats', methods=['GET'])
@token_required
def get_files_stats(current_user):
    """الحصول على إحصائيات الملفات"""
    try:
        # إحصائيات عامة
        total_files = UploadedFile.query.count()
        user_files = UploadedFile.query.filter_by(uploader_id=current_user.id).count()
        public_files = UploadedFile.query.filter_by(is_public=True).count()
        
        # إحصائيات حسب النوع
        type_stats = db.session.query(
            UploadedFile.file_type,
            db.func.count(UploadedFile.id).label('count'),
            db.func.sum(UploadedFile.file_size).label('total_size')
        ).group_by(UploadedFile.file_type).all()
        
        # إحصائيات حسب الفئة
        category_stats = db.session.query(
            UploadedFile.category,
            db.func.count(UploadedFile.id).label('count')
        ).group_by(UploadedFile.category).all()
        
        # حساب المساحة المستخدمة
        total_size = db.session.query(db.func.sum(UploadedFile.file_size)).scalar() or 0
        user_size = db.session.query(db.func.sum(UploadedFile.file_size)).filter_by(
            uploader_id=current_user.id
        ).scalar() or 0
        
        return jsonify({
            'total_files': total_files,
            'user_files': user_files,
            'public_files': public_files,
            'total_size': total_size,
            'total_size_formatted': format_file_size(total_size),
            'user_size': user_size,
            'user_size_formatted': format_file_size(user_size),
            'type_distribution': [
                {
                    'type': file_type,
                    'count': count,
                    'total_size': total_size or 0,
                    'total_size_formatted': format_file_size(total_size or 0)
                }
                for file_type, count, total_size in type_stats
            ],
            'category_distribution': [
                {
                    'category': category,
                    'count': count
                }
                for category, count in category_stats
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get files stats error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب إحصائيات الملفات'}), 500

def format_file_size(size_bytes):
    """تنسيق حجم الملف"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

@files_bp.route('/files/categories', methods=['GET'])
@token_required
def get_file_categories(current_user):
    """الحصول على قائمة فئات الملفات"""
    try:
        categories = [
            {'value': 'general', 'label': 'عام'},
            {'value': 'forms', 'label': 'نماذج'},
            {'value': 'reports', 'label': 'تقارير'},
            {'value': 'procedures', 'label': 'إجراءات'},
            {'value': 'training', 'label': 'تدريب'},
            {'value': 'maintenance', 'label': 'صيانة'},
            {'value': 'inspections', 'label': 'تشييكات'},
            {'value': 'certificates', 'label': 'شهادات'},
            {'value': 'manuals', 'label': 'أدلة'},
            {'value': 'policies', 'label': 'سياسات'}
        ]
        
        return jsonify({'categories': categories}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get file categories error: {str(e)}")
        return jsonify({'message': 'حدث خطأ في جلب فئات الملفات'}), 500

