SatLink Remote PRO - PRO 2.2.4 Dual Architecture
المطور: مهند سات لنك

هذه النسخة تجهز إصدارين منفصلين لويندوز:

1) Windows-x64
   للحاسبات التي يظهر فيها System type: x64-based PC

2) Windows-x86
   للحاسبات التي يظهر فيها System type: x86-based PC

المهم:
- لا يمكن إنشاء ملف EXE واحد أصلي يعمل كـ x64 وx86 معاً.
- سكربت START_CORRECT_WINDOWS_VERSION.bat يكتشف نظام الحاسبة ويشغل المجلد المناسب.
- داخل كل مجلد يبقى البرنامج والسيرفر جنب بعض:
  SatLinkRemotePRO.exe
  SatLinkRelayServer.exe
  server_config.json
- عند تشغيل SatLinkRemotePRO.exe يشغل SatLinkRelayServer.exe تلقائياً إذا لم يكن يعمل.

طريقة البناء:
1. ثبت Python 3.11 64-bit مع Python Launcher.
2. ثبت Python 3.11 32-bit مع Python Launcher على نفس حاسبة البناء.
3. شغل BUILD_DUAL_ARCH_RELEASE.bat.
4. الناتج يظهر داخل:
   dist-dual\SatLinkRemotePRO_DUAL

طريقة الاستخدام على الحاسبة الأخرى:
1. انقل مجلد SatLinkRemotePRO_DUAL كاملاً.
2. شغل START_CORRECT_WINDOWS_VERSION.bat.
3. أو افتح المجلد المناسب يدوياً وشغل SatLinkRemotePRO.exe.

ملاحظات توافق:
- x64 لا يعمل على Windows 32-bit.
- x86 يعمل على Windows 32-bit، وغالباً يعمل أيضاً على Windows 64-bit، لكن الأفضل استخدام x64 على الحاسبات الحديثة.
- Windows ARM64 ليس بناءً أصلياً في هذه الحزمة؛ يجرب مجلد x64 عبر محاكاة Windows إن كانت متاحة.
- بعض إصدارات Windows القديمة جداً قد لا تدعم Python 3.11/PyInstaller الناتج حتى لو كانت 32-bit. النسخة المستهدفة عملياً Windows 10/11.
