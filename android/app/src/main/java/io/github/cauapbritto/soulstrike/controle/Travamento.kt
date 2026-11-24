package io.github.cauapbritto.soulstrike.controle

import android.content.Context
import android.os.Build
import java.io.File

/**
 * Quando o app fecha sozinho (um erro que ninguém pegou), guarda o erro num arquivo. Na próxima
 * vez que abre, o app mostra o erro numa tela (com COPIAR) em vez de ir direto para o menu, e assim
 * dá para mandar o texto e consertar sem precisar do "Ver histórico" do Android.
 */
object Travamento {
    private const val ARQUIVO = "ultimo_erro.txt"

    @Volatile private var instalado = false

    fun instalar(context: Context) {
        if (instalado) return
        instalado = true
        val ctx = context.applicationContext
        val anterior = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { linha, erro ->
            try {
                val texto = buildString {
                    append("SOUL STRIKE CONTROLE v").append(BuildConfig.VERSION_NAME)
                    append(" · ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
                    append(" · ANDROID ").append(Build.VERSION.RELEASE)
                    append(" · ").append(linha.name).append('\n')
                    append(erro.stackTraceToString())
                }
                File(ctx.filesDir, ARQUIVO).writeText(texto.take(12000))
            } catch (e: Throwable) {
                // sem disco: o Android mostra o erro dele
            }
            anterior?.uncaughtException(linha, erro)
        }
    }

    /** O erro da última vez que o app fechou sozinho, ou null. */
    fun ler(context: Context): String? = try {
        File(context.applicationContext.filesDir, ARQUIVO).takeIf { it.exists() }?.readText()?.ifBlank { null }
    } catch (e: Exception) {
        null
    }

    fun esquecer(context: Context) {
        try {
            File(context.applicationContext.filesDir, ARQUIVO).delete()
        } catch (e: Exception) {
            // nada
        }
    }
}
