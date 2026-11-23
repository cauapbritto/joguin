// O Kotlin vem embutido no plugin do Android (AGP 9). O compilador do Compose precisa ser da
// mesma versão do Kotlin, então as duas ficam presas aqui juntas (2.4.10).
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.10")
    }
}

plugins {
    id("com.android.application") version "9.5.0" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.4.10" apply false
}
