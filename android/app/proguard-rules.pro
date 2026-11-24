# O app não usa reflexão: as regras das bibliotecas (Compose, CameraX, ML Kit) já vêm com elas.

# Leitor de QR (ML Kit, modelo embutido): o código nativo do leitor acha classes e campos pelo
# nome, e o R8 no modo completo renomeia/apaga o que ninguém chama em Kotlin. Sem isto, abrir a
# câmera podia fechar o app com "ponto nulo".
-keep class com.google.mlkit.** { *; }
-keep class com.google.android.gms.internal.mlkit_vision_barcode.** { *; }
-keep class com.google.android.gms.internal.mlkit_vision_barcode_bundled.** { *; }
-keep class com.google.android.gms.internal.mlkit_vision_common.** { *; }
-keep class com.google.android.gms.internal.mlkit_common.** { *; }
-keep class * implements com.google.firebase.components.ComponentRegistrar { <init>(); }
-keepclasseswithmembernames class * { native <methods>; }
