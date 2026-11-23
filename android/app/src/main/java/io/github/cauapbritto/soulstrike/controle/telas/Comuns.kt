package io.github.cauapbritto.soulstrike.controle.telas

import android.os.SystemClock
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.style.TextAlign
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Icone
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.aoTocar
import io.github.cauapbritto.soulstrike.controle.ui.corVaga
import io.github.cauapbritto.soulstrike.controle.ui.mistura
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.piscando
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlinx.coroutines.delay

/** Engole todos os toques (o que está embaixo de um aviso não recebe nada). */
fun Modifier.bloquearToques(): Modifier = pointerInput(Unit) {
    awaitPointerEventScope {
        while (true) {
            awaitPointerEvent().changes.forEach { it.consume() }
        }
    }
}

/** Fundo escuro por cima da tela, com uma caixa no meio. */
@Composable
fun Sobreposicao(
    escurecer: Float = 0.82f,
    brilho: Color? = null,
    conteudo: @Composable BoxScope.() -> Unit,
) {
    Box(
        Modifier
            .fillMaxSize()
            .drawBehind {
                drawRect(Color(0xFF0C0A14).copy(alpha = escurecer))
                if (brilho != null) {
                    drawRect(
                        Brush.radialGradient(
                            0f to brilho.copy(alpha = 0.22f), 1f to Color.Transparent,
                            center = center, radius = size.minDimension * 0.9f,
                        )
                    )
                }
            }
            .bloquearToques(),
        contentAlignment = Alignment.Center,
        content = conteudo,
    )
}

/** Recado curto embaixo da tela (some sozinho). */
@Composable
fun Aviso() {
    val app = LocalApp.current
    val texto = app.canal.aviso ?: return
    val m = LocalMedidas.current
    LaunchedEffect(texto) {
        delay(5000)
        if (app.canal.aviso == texto) app.canal.aviso = null
    }
    Box(Modifier.fillMaxSize().padding(bottom = 18.u), contentAlignment = Alignment.BottomCenter) {
        Box(
            Modifier
                .moldura(m, fundo = Cores.Papel, luz = Color.White, sombra = Color(0xFFC9BFA5))
                .padding(horizontal = 12.u, vertical = 8.u)
        ) {
            Texto(texto, cor = Cores.Tinta, alinhar = TextAlign.Center)
        }
    }
}

/** O voltar do Android no meio do jogo: pergunta antes de largar a vaga. */
@Composable
fun ConfirmarSaida(aoFechar: () -> Unit) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    Sobreposicao {
        Column(
            Modifier
                .widthIn(max = 420.u)
                .moldura(m, fundo = Cores.Ink2)
                .padding(16.u),
            verticalArrangement = Arrangement.spacedBy(12.u),
        ) {
            Texto("SAIR DO JOGO?", tam = 16, cor = Cores.Brass, sombra = true)
            val v = canal.vaga
            Texto(
                if (v != 0) "A VAGA P$v FICA LIVRE PARA OUTRO CELULAR. DÁ PARA VOLTAR PELO MENU DE CONEXÃO."
                else "VOLTA PARA O MENU DE CONEXÃO.",
                cor = Cores.Muted,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.u)) {
                Botao("CONTINUAR", Modifier.weight(1f), tipo = TipoBotao.VERDE, aoTocar = aoFechar)
                if (v != 0) {
                    Botao("TROCAR JOGADOR", Modifier.weight(1f), aoTocar = {
                        aoFechar()
                        canal.trocarVaga()
                    })
                }
                Botao("SAIR", Modifier.weight(1f), tipo = TipoBotao.VERMELHO, icone = R.drawable.ic_voltar, aoTocar = {
                    aoFechar()
                    canal.sair()
                })
            }
        }
    }
}

/** Enquanto o app fala com o jogo pela primeira vez. */
@Composable
fun TelaConectando() {
    val app = LocalApp.current
    val canal = app.canal
    val pisca by piscando(400L)
    Column(
        Modifier.fillMaxSize().padding(24.u),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icone(R.drawable.ic_rede, 64, filtro = null, alpha = if (pisca) 1f else 0.55f)
        Spacer(Modifier.height(16.u))
        Texto("CONECTANDO" + if (pisca) "..." else ".  ", tam = 16, cor = Cores.Brass, sombra = true)
        Spacer(Modifier.height(8.u))
        Texto(canal.endereco?.let { "${it.host}:${it.porta}" } ?: "", cor = Cores.Muted)
        Spacer(Modifier.height(20.u))
        Botao("CANCELAR", Modifier.width(200.u), aoTocar = { canal.sair() })
    }
}

/** A Wi-Fi caiu no meio do jogo: o app tenta de novo sozinho e a vaga fica guardada. */
@Composable
fun TelaCaiu() {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    var agora by remember { mutableLongStateOf(SystemClock.elapsedRealtime()) }
    LaunchedEffect(Unit) {
        while (true) {
            agora = SystemClock.elapsedRealtime()
            delay(250)
        }
    }
    val passou = ((agora - canal.caiuEm) / 1000L).toInt() + 3        // o vigia avisa 3 s depois do último sinal
    val resta = (GUARDA_VAGA - passou).coerceAtLeast(0)
    val v = canal.vaga
    Sobreposicao(escurecer = 0.78f, brilho = Cores.Blood) {
        Row(
            Modifier
                .widthIn(max = 560.u)
                .moldura(m, fundo = Cores.Ink2)
                .padding(16.u),
            horizontalArrangement = Arrangement.spacedBy(16.u),
        ) {
            Icone(R.drawable.ic_wifi_off, 64, sombra = true)
            Column(verticalArrangement = Arrangement.spacedBy(8.u), modifier = Modifier.weight(1f)) {
                Texto("CONEXÃO CAIU", tam = 16, cor = Cores.Blood, sombra = true)
                Texto(
                    "TENTANDO DE NOVO SOZINHO (${canal.tentativas}ª VEZ)...\nO JOGO SOLTOU SEUS BOTÕES NA HORA.",
                    cor = Cores.Muted,
                )
                if (v != 0) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Texto(
                            if (resta > 0) "SUA VAGA P$v FICA GUARDADA" else "A VAGA P$v PODE TER SIDO LIBERADA",
                            Modifier.weight(1f), cor = Cores.Bone,
                        )
                        if (resta > 0) Texto("$resta S", cor = Cores.Brass)
                    }
                    val cor = corVaga(v)
                    Spacer(
                        Modifier
                            .fillMaxWidth()
                            .height(8.u)
                            .drawBehind {
                                val n = GUARDA_VAGA
                                val gap = m.px(2)
                                val w = (size.width - gap * (n - 1)) / n
                                for (i in 0 until n) {
                                    drawRect(
                                        if (i < resta) cor else Color(0xFF2D2742),
                                        Offset(i * (w + gap), 0f), Size(w, size.height),
                                    )
                                }
                            }
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.u), modifier = Modifier.padding(top = 4.u)) {
                    Botao("TENTAR AGORA", Modifier.weight(1f), tipo = TipoBotao.VERDE, aoTocar = { canal.tentarAgora() })
                    Botao("MENU DE CONEXÃO", Modifier.weight(1f), icone = R.drawable.ic_voltar, aoTocar = { canal.sair() })
                }
            }
        }
    }
}

/** Segundos que o jogo guarda a vaga de quem caiu (RELEASE do remote.py). */
private const val GUARDA_VAGA = 20

/** "HÁ 2 MIN", "ONTEM", "12 NOV"... */
fun quando(ms: Long): String {
    if (ms <= 0L) return ""
    val d = (System.currentTimeMillis() - ms) / 1000L
    return when {
        d < 60 -> "AGORA"
        d < 3600 -> "HÁ ${d / 60} MIN"
        d < 86400 -> "HÁ ${d / 3600} H"
        d < 2 * 86400 -> "ONTEM"
        else -> {
            val c = java.util.Calendar.getInstance().apply { timeInMillis = ms }
            val meses = arrayOf("JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")
            "${c.get(java.util.Calendar.DAY_OF_MONTH)} ${meses[c.get(java.util.Calendar.MONTH)]}"
        }
    }
}

/** Nome do modo como a TV mostra. */
fun nomeDoModo(modo: String, hud: String = ""): String = when (modo) {
    "soccer" -> if (hud == "basket") "BASQUETE" else "FUTEBOL"
    "campaign" -> "CAMPANHA"
    "luta" -> "LUTA"
    "battle" -> "DUELO"
    else -> modo.uppercase()
}

/** Um quadrado da vaga (escolha de jogador e jogos na rede): o número na cor e LIVRE embaixo. */
@Composable
fun BotaoVaga(
    n: Int,
    estado: String,
    livre: Boolean,
    modifier: Modifier = Modifier,
    numero: Int = 24,
    ativo: Boolean = true,
    aoTocar: () -> Unit,
) {
    val m = LocalMedidas.current
    val cor = corVaga(n)
    val apertado = remember { mutableStateOf(false) }
    Column(
        modifier
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .moldura(m, fundo = Cores.Ink3)
            .aoTocar(ativo = ativo, apertado = apertado, acao = aoTocar)
            .padding(4.u),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .drawBehind {
                    drawRect(
                        Brush.radialGradient(
                            0f to mistura(cor, if (livre) 0.4f else 0.12f, Color(0xFF1A1628)),
                            0.75f to Color(0xFF120F1E),
                            center = Offset(size.width / 2f, size.height * 0.55f),
                            radius = size.maxDimension * 0.75f,
                        )
                    )
                    drawRect(Color.Black.copy(alpha = 0.55f), size = Size(size.width, m.px(2)))
                    drawRect(Color.Black.copy(alpha = 0.55f), size = Size(m.px(2), size.height))
                },
            contentAlignment = Alignment.Center,
        ) {
            Texto("$n", tam = numero, cor = if (livre) cor else Cores.Dim, sombra = true, linha = numero)
        }
        Box(
            Modifier
                .fillMaxWidth()
                .padding(top = 4.u)
                .drawBehind { drawRect(Color(0xFF0E0B18)) }
                .padding(top = 4.u, bottom = 2.u),
            contentAlignment = Alignment.Center,
        ) {
            Texto(estado, cor = if (livre) cor else Cores.Dim, linhas = 1)
        }
    }
}
