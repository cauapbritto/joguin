package io.github.cauapbritto.soulstrike.controle.telas

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.u

/** QUAL JOGADOR É VOCÊ? As 4 vagas na cor de cada uma (ocupada fica apagada). */
@Composable
fun TelaVagas() {
    val app = LocalApp.current
    val canal = app.canal
    val st = canal.status
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val altura: Dp = (maxHeight * 0.3f).coerceIn(72.u, 120.u)
        Column(
            Modifier
                .fillMaxSize()
                .padding(horizontal = 20.u, vertical = 12.u),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Logo(
                Modifier
                    .fillMaxWidth(0.5f)
                    .height(48.u)
            )
            Spacer(Modifier.height(14.u))
            Texto("QUAL JOGADOR É VOCÊ?", tam = 16, cor = Cores.Bone, sombra = true, alinhar = TextAlign.Center)
            Spacer(Modifier.height(14.u))
            Row(horizontalArrangement = Arrangement.spacedBy(14.u)) {
                for (n in 1..4) {
                    val ocupada = st?.vagas?.get(n)?.conectada == true
                    BotaoVaga(
                        n, if (ocupada) "OCUPADO" else "LIVRE", livre = !ocupada,
                        modifier = Modifier.size(width = 96.u, height = altura),
                    ) { canal.escolherVaga(n) }
                }
            }
            Spacer(Modifier.height(14.u))
            val erro = canal.erro
            Texto(
                erro ?: "MESMA REDE WI-FI DO COMPUTADOR · O NÚMERO É A SUA COR NA TV",
                cor = if (erro != null) Cores.Blood else Cores.Muted,
                alinhar = TextAlign.Center,
            )
        }
        Row(
            Modifier
                .fillMaxWidth()
                .padding(12.u),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Botao("SAIR", icone = R.drawable.ic_voltar, altura = 32) { canal.sair() }
            Spacer(Modifier.weight(1f))
            Box(Modifier.width(8.dp))
            Sinal(canal.rtt, Modifier.size(16.u))
            Spacer(Modifier.width(6.u))
            Texto(canal.nomePc.ifEmpty { canal.endereco?.host ?: "" }, cor = Cores.Muted, linhas = 1)
        }
    }
}
