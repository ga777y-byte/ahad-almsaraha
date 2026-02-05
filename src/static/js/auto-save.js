/**
 * نظام الحفظ التلقائي والمزامنة المشتركة
 * يدعم حفظ البيانات في localStorage, sessionStorage, وIndexedDB
 * مع مزامنة فورية بين جميع المستخدمين
 */

class AutoSaveSystem {
    constructor(options = {}) {
        this.options = {
            saveInterval: options.saveInterval || 5000, // 5 ثوان
            quickSaveDelay: options.quickSaveDelay || 2000, // 2 ثانية للحفظ السريع
            enableIndexedDB: options.enableIndexedDB !== false,
            enableSync: options.enableSync !== false,
            storagePrefix: options.storagePrefix || 'hospital_fire_safety_',
            ...options
        };

        this.isInitialized = false;
        this.saveTimeout = null;
        this.quickSaveTimeout = null;
        this.lastSaveTime = null;
        this.pendingData = new Map();
        this.syncInterval = null;
        
        this.init();
    }

    async init() {
        if (this.isInitialized) return;

        try {
            // تهيئة IndexedDB إذا كان مفعلاً
            if (this.options.enableIndexedDB) {
                await this.initIndexedDB();
            }

            // بدء الحفظ التلقائي
            this.startAutoSave();

            // بدء المزامنة إذا كانت مفعلة
            if (this.options.enableSync) {
                this.startSync();
            }

            // إضافة مستمعي الأحداث
            this.addEventListeners();

            // استعادة البيانات المحفوظة
            this.restoreData();

            this.isInitialized = true;
            this.showIndicator('تم تهيئة نظام الحفظ التلقائي', 'success');
            
            console.log('Auto-save system initialized successfully');
        } catch (error) {
            console.error('Error initializing auto-save system:', error);
            this.showIndicator('خطأ في تهيئة نظام الحفظ التلقائي', 'error');
        }
    }

    async initIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('HospitalFireSafetyDB', 1);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // إنشاء مخزن البيانات
                if (!db.objectStoreNames.contains('autoSaveData')) {
                    const store = db.createObjectStore('autoSaveData', { keyPath: 'key' });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('userId', 'userId', { unique: false });
                }
                
                // إنشاء مخزن الملفات
                if (!db.objectStoreNames.contains('files')) {
                    const fileStore = db.createObjectStore('files', { keyPath: 'id' });
                    fileStore.createIndex('name', 'name', { unique: false });
                    fileStore.createIndex('type', 'type', { unique: false });
                    fileStore.createIndex('uploadDate', 'uploadDate', { unique: false });
                }
            };
        });
    }

    startAutoSave() {
        // حفظ دوري كل فترة محددة
        this.saveInterval = setInterval(() => {
            this.saveAll();
        }, this.options.saveInterval);
    }

    startSync() {
        // مزامنة مع الخادم كل 30 ثانية
        this.syncInterval = setInterval(() => {
            this.syncWithServer();
        }, 30000);
    }

    addEventListeners() {
        // حفظ عند تغيير أي حقل إدخال
        document.addEventListener('input', (e) => {
            if (e.target.matches('input, textarea, select')) {
                this.scheduleQuickSave(e.target);
            }
        });

        // حفظ عند تغيير checkbox أو radio
        document.addEventListener('change', (e) => {
            if (e.target.matches('input[type="checkbox"], input[type="radio"]')) {
                this.scheduleQuickSave(e.target);
            }
        });

        // حفظ عند إغلاق النافذة أو فقدان التركيز
        window.addEventListener('beforeunload', () => {
            this.saveNow();
        });

        window.addEventListener('blur', () => {
            this.saveNow();
        });

        // حفظ عند الضغط على Ctrl+S
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                this.saveNow();
                this.showIndicator('تم الحفظ يدوياً', 'success');
            }
        });

        // حفظ عند تغيير الصفحة
        window.addEventListener('pagehide', () => {
            this.saveNow();
        });
    }

    scheduleQuickSave(element) {
        // إلغاء المهلة السابقة
        if (this.quickSaveTimeout) {
            clearTimeout(this.quickSaveTimeout);
        }

        // إضافة البيانات إلى قائمة الانتظار
        const key = this.getElementKey(element);
        const value = this.getElementValue(element);
        this.pendingData.set(key, {
            value: value,
            timestamp: Date.now(),
            element: element.tagName.toLowerCase(),
            type: element.type || 'text'
        });

        // جدولة الحفظ السريع
        this.quickSaveTimeout = setTimeout(() => {
            this.saveNow();
        }, this.options.quickSaveDelay);

        // إظهار مؤشر الحفظ
        this.showIndicator('جاري الحفظ...', 'saving');
    }

    getElementKey(element) {
        // إنشاء مفتاح فريد للعنصر
        const page = window.location.pathname;
        const id = element.id || element.name || element.className;
        const index = Array.from(document.querySelectorAll(element.tagName)).indexOf(element);
        return `${this.options.storagePrefix}${page}_${id}_${index}`;
    }

    getElementValue(element) {
        switch (element.type) {
            case 'checkbox':
                return element.checked;
            case 'radio':
                return element.checked ? element.value : null;
            case 'file':
                return Array.from(element.files).map(f => ({
                    name: f.name,
                    size: f.size,
                    type: f.type,
                    lastModified: f.lastModified
                }));
            default:
                return element.value;
        }
    }

    async saveNow() {
        if (this.pendingData.size === 0) return;

        try {
            const dataToSave = Object.fromEntries(this.pendingData);
            const userId = this.getCurrentUserId();
            const timestamp = Date.now();

            // حفظ في localStorage
            localStorage.setItem(`${this.options.storagePrefix}autoSave`, JSON.stringify({
                data: dataToSave,
                timestamp: timestamp,
                userId: userId
            }));

            // حفظ في sessionStorage
            sessionStorage.setItem(`${this.options.storagePrefix}session`, JSON.stringify({
                data: dataToSave,
                timestamp: timestamp,
                userId: userId
            }));

            // حفظ في IndexedDB إذا كان متاحاً
            if (this.db) {
                await this.saveToIndexedDB(dataToSave, userId, timestamp);
            }

            // مزامنة مع الخادم
            if (this.options.enableSync) {
                await this.syncWithServer(dataToSave);
            }

            this.lastSaveTime = timestamp;
            this.pendingData.clear();
            
            this.showIndicator('تم الحفظ بنجاح', 'success');
            console.log('Data saved successfully at', new Date(timestamp));

        } catch (error) {
            console.error('Error saving data:', error);
            this.showIndicator('خطأ في الحفظ', 'error');
        }
    }

    async saveAll() {
        // حفظ جميع البيانات الموجودة في النماذج
        const forms = document.querySelectorAll('form');
        const inputs = document.querySelectorAll('input, textarea, select');
        
        inputs.forEach(input => {
            if (input.type !== 'password' && input.type !== 'submit' && input.type !== 'button') {
                const key = this.getElementKey(input);
                const value = this.getElementValue(input);
                this.pendingData.set(key, {
                    value: value,
                    timestamp: Date.now(),
                    element: input.tagName.toLowerCase(),
                    type: input.type || 'text'
                });
            }
        });

        if (this.pendingData.size > 0) {
            await this.saveNow();
        }
    }

    async saveToIndexedDB(data, userId, timestamp) {
        if (!this.db) return;

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['autoSaveData'], 'readwrite');
            const store = transaction.objectStore('autoSaveData');
            
            const saveData = {
                key: `${userId}_${window.location.pathname}`,
                data: data,
                userId: userId,
                timestamp: timestamp,
                page: window.location.pathname
            };
            
            const request = store.put(saveData);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async syncWithServer(data = null) {
        try {
            const token = localStorage.getItem('userToken');
            if (!token) return;

            const syncData = data || Object.fromEntries(this.pendingData);
            
            const response = await fetch('/api/sync/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    data: syncData,
                    timestamp: Date.now(),
                    page: window.location.pathname
                })
            });

            if (response.ok) {
                console.log('Data synced with server successfully');
            }
        } catch (error) {
            console.error('Error syncing with server:', error);
        }
    }

    async restoreData() {
        try {
            // استعادة من localStorage
            const localData = localStorage.getItem(`${this.options.storagePrefix}autoSave`);
            if (localData) {
                const parsed = JSON.parse(localData);
                this.restoreFormData(parsed.data);
            }

            // استعادة من IndexedDB إذا كان متاحاً
            if (this.db) {
                const indexedData = await this.getFromIndexedDB();
                if (indexedData) {
                    this.restoreFormData(indexedData.data);
                }
            }

            // استعادة من الخادم
            if (this.options.enableSync) {
                await this.restoreFromServer();
            }

        } catch (error) {
            console.error('Error restoring data:', error);
        }
    }

    async getFromIndexedDB() {
        if (!this.db) return null;

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['autoSaveData'], 'readonly');
            const store = transaction.objectStore('autoSaveData');
            const userId = this.getCurrentUserId();
            const key = `${userId}_${window.location.pathname}`;
            
            const request = store.get(key);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async restoreFromServer() {
        try {
            const token = localStorage.getItem('userToken');
            if (!token) return;

            const response = await fetch(`/api/sync/restore?page=${encodeURIComponent(window.location.pathname)}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.data) {
                    this.restoreFormData(data.data);
                }
            }
        } catch (error) {
            console.error('Error restoring from server:', error);
        }
    }

    restoreFormData(data) {
        Object.entries(data).forEach(([key, item]) => {
            const element = this.findElementByKey(key);
            if (element && item.value !== null && item.value !== undefined) {
                this.setElementValue(element, item.value);
            }
        });
    }

    findElementByKey(key) {
        // البحث عن العنصر باستخدام المفتاح
        const inputs = document.querySelectorAll('input, textarea, select');
        for (const input of inputs) {
            if (this.getElementKey(input) === key) {
                return input;
            }
        }
        return null;
    }

    setElementValue(element, value) {
        switch (element.type) {
            case 'checkbox':
                element.checked = Boolean(value);
                break;
            case 'radio':
                if (value) {
                    element.checked = element.value === value;
                }
                break;
            case 'file':
                // لا يمكن استعادة الملفات لأسباب أمنية
                break;
            default:
                element.value = value;
                break;
        }

        // إطلاق حدث التغيير
        element.dispatchEvent(new Event('change', { bubbles: true }));
    }

    getCurrentUserId() {
        try {
            const userInfo = localStorage.getItem('userInfo');
            if (userInfo) {
                const user = JSON.parse(userInfo);
                return user.id || user.email || 'anonymous';
            }
        } catch (error) {
            console.error('Error getting user ID:', error);
        }
        return 'anonymous';
    }

    showIndicator(message, type = 'info') {
        const indicator = document.getElementById('autoSaveIndicator');
        if (!indicator) return;

        indicator.textContent = message;
        indicator.className = `auto-save-indicator ${type}`;
        indicator.style.display = 'block';

        // إخفاء المؤشر بعد 3 ثوان
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 3000);
    }

    // دوال للتحكم الخارجي
    enable() {
        if (!this.isInitialized) {
            this.init();
        }
        this.startAutoSave();
        if (this.options.enableSync) {
            this.startSync();
        }
    }

    disable() {
        if (this.saveInterval) {
            clearInterval(this.saveInterval);
            this.saveInterval = null;
        }
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
        if (this.quickSaveTimeout) {
            clearTimeout(this.quickSaveTimeout);
            this.quickSaveTimeout = null;
        }
    }

    // تصدير البيانات
    async exportData() {
        try {
            const localData = localStorage.getItem(`${this.options.storagePrefix}autoSave`);
            const sessionData = sessionStorage.getItem(`${this.options.storagePrefix}session`);
            let indexedData = null;

            if (this.db) {
                indexedData = await this.getFromIndexedDB();
            }

            const exportData = {
                localStorage: localData ? JSON.parse(localData) : null,
                sessionStorage: sessionData ? JSON.parse(sessionData) : null,
                indexedDB: indexedData,
                timestamp: Date.now(),
                version: '1.0'
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `hospital_fire_safety_backup_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showIndicator('تم تصدير البيانات بنجاح', 'success');
        } catch (error) {
            console.error('Error exporting data:', error);
            this.showIndicator('خطأ في تصدير البيانات', 'error');
        }
    }

    // استيراد البيانات
    async importData(file) {
        try {
            const text = await file.text();
            const importData = JSON.parse(text);

            if (importData.localStorage) {
                localStorage.setItem(`${this.options.storagePrefix}autoSave`, JSON.stringify(importData.localStorage));
            }

            if (importData.sessionStorage) {
                sessionStorage.setItem(`${this.options.storagePrefix}session`, JSON.stringify(importData.sessionStorage));
            }

            if (importData.indexedDB && this.db) {
                await this.saveToIndexedDB(
                    importData.indexedDB.data,
                    importData.indexedDB.userId,
                    importData.indexedDB.timestamp
                );
            }

            // استعادة البيانات المستوردة
            await this.restoreData();

            this.showIndicator('تم استيراد البيانات بنجاح', 'success');
        } catch (error) {
            console.error('Error importing data:', error);
            this.showIndicator('خطأ في استيراد البيانات', 'error');
        }
    }

    // مسح جميع البيانات المحفوظة
    clearAllData() {
        if (confirm('هل أنت متأكد من مسح جميع البيانات المحفوظة؟ هذا الإجراء لا يمكن التراجع عنه.')) {
            // مسح localStorage
            Object.keys(localStorage).forEach(key => {
                if (key.startsWith(this.options.storagePrefix)) {
                    localStorage.removeItem(key);
                }
            });

            // مسح sessionStorage
            Object.keys(sessionStorage).forEach(key => {
                if (key.startsWith(this.options.storagePrefix)) {
                    sessionStorage.removeItem(key);
                }
            });

            // مسح IndexedDB
            if (this.db) {
                const transaction = this.db.transaction(['autoSaveData'], 'readwrite');
                const store = transaction.objectStore('autoSaveData');
                store.clear();
            }

            this.pendingData.clear();
            this.showIndicator('تم مسح جميع البيانات', 'success');
        }
    }

    // إحصائيات النظام
    getStats() {
        const localDataSize = new Blob([localStorage.getItem(`${this.options.storagePrefix}autoSave`) || '']).size;
        const sessionDataSize = new Blob([sessionStorage.getItem(`${this.options.storagePrefix}session`) || '']).size;
        
        return {
            isInitialized: this.isInitialized,
            lastSaveTime: this.lastSaveTime,
            pendingDataCount: this.pendingData.size,
            localStorageSize: localDataSize,
            sessionStorageSize: sessionDataSize,
            indexedDBAvailable: !!this.db,
            syncEnabled: this.options.enableSync
        };
    }
}

// إنشاء مثيل عام للنظام
window.autoSave = new AutoSaveSystem({
    saveInterval: 5000, // 5 ثوان
    quickSaveDelay: 2000, // 2 ثانية
    enableIndexedDB: true,
    enableSync: true,
    storagePrefix: 'hospital_fire_safety_'
});

// تصدير الكلاس للاستخدام في ملفات أخرى
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutoSaveSystem;
}

