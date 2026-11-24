plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

// A versão do app é a do jogo (soulstrike/__init__.py): o APK de cada Release sai com o mesmo número.
val gameVersion: String = run {
    val init = rootProject.file("../soulstrike/__init__.py")
    val text = if (init.exists()) init.readText() else ""
    Regex("__version__\\s*=\\s*\"([0-9.]+)\"").find(text)?.groupValues?.get(1) ?: "1.0.0"
}
val gameVersionCode: Int = gameVersion.split(".").map { it.toIntOrNull() ?: 0 }.let { p ->
    p.getOrElse(0) { 0 } * 10000 + p.getOrElse(1) { 0 } * 100 + p.getOrElse(2) { 0 }
}

android {
    namespace = "io.github.cauapbritto.soulstrike.controle"
    // o Compose de novembro de 2026 pede o Android 17.1 (API 37.1) para compilar
    compileSdk {
        version = release(37) {
            minorApiLevel = 1
        }
    }

    defaultConfig {
        applicationId = "io.github.cauapbritto.soulstrike.controle"
        minSdk = 26
        targetSdk = 37
        versionCode = gameVersionCode
        versionName = gameVersion
    }

    // Uma chave só, guardada aqui no projeto: o APK do GitHub e o do Android Studio saem com a
    // mesma assinatura, então um atualiza o outro sem desinstalar.
    signingConfigs {
        create("controle") {
            storeFile = file("controle.jks")
            storePassword = "soulstrike-controle"
            keyAlias = "controle"
            keyPassword = "soulstrike-controle"
        }
    }

    buildTypes {
        getByName("debug") {
            signingConfig = signingConfigs.getByName("controle")
        }
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("controle")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.11.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.camera:camera-camera2:1.6.2")
    implementation("androidx.camera:camera-lifecycle:1.6.2")
    implementation("androidx.camera:camera-view:1.6.2")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
}
