package io.github.cauapbritto.soulstrike.controle.telas

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import io.github.cauapbritto.soulstrike.controle.BuildConfig
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.Tela
import io.github.cauapbritto.soulstrike.controle.rede.Endereco
import io.github.cauapbritto.soulstrike.controle.rede.JogoAchado
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Icone
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.filtroCinza
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.piscando
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlinx.coroutines.delay

/** JOGOS NA REDE: cada jogo aberto na Wi-Fi com as 4 vagas; um toque na vaga já entra. */
@Composable
fun TelaRede() {
    val app = LocalApp.current
    val d = app.descoberta
    LaunchedEffect(Unit) {
        while (true) {                   // procura de novo a cada pouco: vagas e jogos mudam
            if (!d.procurando) d.procurar(3)
            delay(6000)
        }
    }
    DisposableEffect(Unit) { onDispose { d.parar() } }
    val pisca by piscando(500L)
    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Botao("VOLTAR", icone = R.drawable.ic_voltar, altura = 32) { app.tela = Tela.MENU }
            Texto("JOGOS NA REDE", tam = 16, sombra = true, modifier = Modifier.weight(1f), linhas = 1)
            Icone(R.drawable.ic_rede, 16, alpha = if (d.procurando && pisca) 0.5f else 1f)
            Texto(
                if (d.procurando) "PROCURANDO NA WI-FI..." else "${d.jogos.size} NA WI-FI",
                cor = Cores.Muted, linhas = 1,
            )
        }
        Column(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.u, vertical = 14.u),
            verticalArrangement = Arrangement.spacedBy(14.u),
        ) {
            if (d.jogos.isEmpty()) {
                Box(Modifier.fillMaxWidth().height(120.u), contentAlignment = Alignment.Center) {
                    Texto(
                        if (d.procurando) "PROCURANDO..." else "NENHUM JOGO RESPONDEU AINDA",
                        tam = 16, cor = Cores.Muted,
                    )
                }
            }
            for (j in d.jogos) {
                CartaoJogo(j) { vaga -> app.conectar(Endereco(j.host, j.porta, vaga)) }
            }
        }
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 16.u, end = 16.u, bottom = 12.u),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.u),
        ) {
            Texto(
                "NÃO APARECEU? O CELULAR PRECISA ESTAR NA MESMA WI-FI DO COMPUTADOR, COM O JOGO ABERTO.",
                Modifier.weight(1f), cor = Cores.Muted,
            )
            Botao("PROCURAR DE NOVO", icone = R.drawable.i_trocar, ativo = !d.procurando) { d.procurar() }
            Botao("DIGITAR ENDEREÇO", icone = R.drawable.ic_teclado) { app.tela = Tela.DIGITAR }
        }
    }
}

/** Um jogo achado: nome do computador, versão, modo, sinal e as 4 vagas. */
@Composable
private fun CartaoJogo(j: JogoAchado, aoEscolher: (Int) -> Unit) {
    val m = LocalMedidas.current
    val velho = versaoMenor(j.versao, BuildConfig.VERSION_NAME)
    val novo = j.protocolo > 1
    Row(
        Modifier
            .fillMaxWidth()
            .moldura(m, fundo = Cores.Ink3)
            .padding(14.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.u),
    ) {
        Box(
            Modifier
                .size(64.u)
                .drawBehind {
                    drawRect(Color(0xFF15111F))
                    drawRect(
                        Brush.radialGradient(
                            0f to Color(0x664A8CFF), 1f to Color.Transparent,
                            center = center, radius = size.minDimension * 0.7f,
                        )
                    )
                },
            contentAlignment = Alignment.Center,
        ) {
            Icone(R.drawable.ic_pc, 48, filtro = if (velho) filtroCinza(0.8f) else null, sombra = true)
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.u)) {
            Texto(j.nome, tam = 16, sombra = true, linhas = 1)
            val modo = if (j.fase == "menu" || j.fase.isEmpty()) "NO MENU" else nomeDoModo(j.modo)
            Texto("SOUL STRIKE v${j.versao} · $modo", cor = Cores.Muted, linhas = 1)
            when {
                novo -> Texto("APP DESATUALIZADO: BAIXE O APK DA VERSÃO NOVA", cor = Cores.Brass)
                velho -> Texto("JOGO DESATUALIZADO: USE O ATUALIZAR DO JOGO", cor = Cores.Brass)
                else -> Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.u)) {
                    Sinal(j.ms, Modifier.size(16.u))
                    Texto("SINAL ${forcaDoSinal(j.ms)} · ${j.ms} MS", cor = corDoSinal(j.ms))
                }
            }
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.u)) {
            Texto("TOQUE NA SUA VAGA", cor = Cores.Brass)
            Row(horizontalArrangement = Arrangement.spacedBy(8.u)) {
                for (n in 1..4) {
                    val v = j.vagas[n]
                    val usando = v?.conectada == true
                    val guardada = v?.ocupada == true && !usando
                    BotaoVaga(
                        n,
                        if (usando) "EM USO" else if (guardada) "GUARDADA" else "LIVRE",
                        livre = !usando,
                        ativo = !usando && !novo,
                        numero = 16,
                        modifier = Modifier.size(width = 58.u, height = 64.u),
                    ) { aoEscolher(n) }
                }
            }
        }
    }
}

/** Barrinhas de sinal: 4 quando o jogo responde rápido. */
@Composable
fun Sinal(ms: Int, modifier: Modifier = Modifier) {
    val m = LocalMedidas.current
    val barras = when {
        ms < 0 -> 0
        ms < 40 -> 4
        ms < 90 -> 3
        ms < 180 -> 2
        else -> 1
    }
    val cor = corDoSinal(ms)
    Box(
        modifier.drawBehind {
            val w = m.px(3)
            val gap = m.px(1)
            for (i in 0 until 4) {
                val h = size.height * (i + 1) / 4f
                drawRect(
                    if (i < barras) cor else Color(0xFF3A3156),
                    Offset(i * (w + gap), size.height - h), Size(w, h),
                )
            }
        }
    )
}

fun corDoSinal(ms: Int): Color = when {
    ms < 0 -> Cores.Muted
    ms < 90 -> Cores.Moss
    ms < 180 -> Color(0xFFE0B44C)
    else -> Color(0xFFE06B5A)
}

private fun forcaDoSinal(ms: Int): String = when {
    ms < 40 -> "FORTE"
    ms < 90 -> "BOM"
    ms < 180 -> "MÉDIO"
    else -> "FRACO"
}

/** "1.52.0" < "1.59.0"? */
fun versaoMenor(a: String, b: String): Boolean {
    val pa = a.split(".").map { it.toIntOrNull() ?: 0 }
    val pb = b.split(".").map { it.toIntOrNull() ?: 0 }
    if (pa.all { it == 0 } || pb.all { it == 0 }) return false
    for (i in 0 until maxOf(pa.size, pb.size)) {
        val x = pa.getOrElse(i) { 0 }
        val y = pb.getOrElse(i) { 0 }
        if (x != y) return x < y
    }
    return false
}
