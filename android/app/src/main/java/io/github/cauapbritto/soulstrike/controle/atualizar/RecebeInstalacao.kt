package io.github.cauapbritto.soulstrike.controle.atualizar

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.os.Build
import io.github.cauapbritto.soulstrike.controle.AppEstado

/**
 * A resposta do instalador do Android. Na primeira vez ele pede para o jogador confirmar
 * (STATUS_PENDING_USER_ACTION traz a tela de confirmação); depois, instala e fecha o app.
 */
class RecebeInstalacao : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val atualizador = AppEstado.de(context).atualizador
        when (val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val confirmar: Intent? = if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent.getParcelableExtra(Intent.EXTRA_INTENT)
                }
                if (confirmar == null) {
                    atualizador.terminou(false, null)
                    return
                }
                try {
                    context.startActivity(confirmar.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                } catch (e: Exception) {
                    atualizador.terminou(false, "o Android não abriu a confirmação")
                }
            }
            PackageInstaller.STATUS_SUCCESS -> atualizador.terminou(true, null)
            PackageInstaller.STATUS_FAILURE_ABORTED -> atualizador.terminou(false, null)
            else -> atualizador.terminou(false, intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: "erro $status")
        }
    }

    companion object {
        const val ACAO = "io.github.cauapbritto.soulstrike.controle.INSTALOU"
    }
}
