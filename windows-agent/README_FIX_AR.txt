حل مشكلة Pillow / qrcode على Windows

إذا ظهر عندك الخطأ:
Pillow 10.4.0 does not support Python 3.14
أو:
ModuleNotFoundError: No module named qrcode

فالسبب أن الجهاز يستخدم Python 3.14.
الحل الصحيح: ثبت Python 3.12 أو Python 3.11 ثم شغل run.bat الجديد.

الأوامر اليدوية إذا أردت تثبيت المكتبات بنفسك:

py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py

إذا كان عندك Python 3.11 بدل 3.12 استخدم:

py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 main.py

ملاحظة:
لا تستخدم Python 3.14 لهذه النسخة لأن بعض مكتبات التصوير على Windows لا توفر ملفات جاهزة له وقد تحاول البناء من المصدر وتفشل.
