package io.github.cauapbritto.soulstrike.controle

import android.content.Context
import android.content.Intent
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat

/**
 * Segurar o ícone do app mostra VOLTAR AO <COMPUTADOR>: entra direto no último jogo, na mesma vaga
 * (o mesmo caminho do VOLTAR AO... do menu). Atualiza a cada vez que o celular entra num jogo.
 */
object Atalhos {
    fun voltarAo(ctx: Context, jogo: JogoSalvo) {
        try {
            val nome = jogo.nome.ifEmpty { jogo.host }
            val abrir = Intent(ctx, MainActivity::class.java)
                .setAction(Intent.ACTION_VIEW)
                .putExtra("host", jogo.host)
                .putExtra("porta", jogo.porta)
                .putExtra("vaga", jogo.vaga)
            val atalho = ShortcutInfoCompat.Builder(ctx, "voltar")
                .setShortLabel("VOLTAR AO JOGO")
                .setLongLabel("VOLTAR AO $nome".take(25))
                .setIcon(IconCompat.createWithResource(ctx, R.mipmap.ic_launcher))
                .setIntent(abrir)
                .build()
            ShortcutManagerCompat.pushDynamicShortcut(ctx, atalho)
        } catch (e: Exception) {
            // celular sem atalhos (ou o Android recusou): o VOLTAR AO... do menu continua lá
        }
    }
}
