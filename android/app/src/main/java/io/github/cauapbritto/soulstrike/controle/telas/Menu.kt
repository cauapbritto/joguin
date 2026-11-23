package io.github.cauapbritto.soulstrike.controle.telas

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.imageResource
import androidx.compose.ui.text.style.TextAlign
import io.github.cauapbritto.soulstrike.controle.BuildConfig
import io.github.cauapbritto.soulstrike.controle.JogoSalvo
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.Tela
import io.github.cauapbritto.soulstrike.controle.rede.Descoberta
import io.github.cauapbritto.soulstrike.controle.rede.Endereco
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Icone
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Medidas
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.aoTocar
import io.github.cauapbritto.soulstrike.controle.ui.corVaga
import io.github.cauapbritto.soulstrike.controle.ui.desenharPixel
import io.github.cauapbritto.soulstrike.controle.ui.escalaInteira
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

/** O menu de conexão: ESCANEAR o QR, PROCURAR na rede ou DIGITAR o endereço (e VOLTAR ao último). */
@Composable
fun TelaMenu() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val ultimo = remember { app.prefs.recentes().firstOrNull() }
    var wifi by remember { mutableStateOf(Descoberta.naWifi(ctx)) }
    LaunchedEffect(Unit) {
        app.descoberta.procurar()
        while (true) {
            wifi = Descoberta.naWifi(ctx)
            delay(2000)
        }
    }
    val achados = app.descoberta.jogos.size
    val erro = app.canal.erro
    Box(Modifier.fillMaxSize()) {
        Column(
            Modifier
                .fillMaxSize()
                .padding(horizontal = 24.u, vertical = 12.u),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Logo(
                Modifier
                    .fillMaxWidth(0.6f)
                    .height(60.u)
            )
            Spacer(Modifier.height(6.u))
            Texto("O CELULAR VIRA CONTROLE · MESMA WI-FI DO COMPUTADOR", cor = Cores.Muted, alinhar = TextAlign.Center)
            Spacer(Modifier.height(10.u))
            when {
                app.redeLocalNegada -> Faixa(
                    "O ANDROID BLOQUEOU A REDE LOCAL: SEM ELA O APP NÃO ACHA O JOGO",
                    "PERMITIR",
                ) { app.pedirRedeLocal?.invoke() ?: app.abrirAjustesDoAndroid?.invoke() }
                erro != null -> Faixa(erro, "OK") { app.canal.erro = null }
                ultimo != null -> BarraVoltar(ultimo, Modifier.fillMaxWidth(0.76f)) {
                    app.conectar(Endereco(ultimo.host, ultimo.porta, ultimo.vaga))
                }
            }
            Spacer(Modifier.height(16.u))
            Row(
                Modifier
                    .weight(1f)
                    .fillMaxWidth(0.86f),
                horizontalArrangement = Arrangement.spacedBy(18.u),
            ) {
                CartaoMenu(
                    "ESCANEAR", "O QR DA TV", R.drawable.ic_qr, Color(0xFFB4783C), destaque = true,
                    modifier = Modifier.weight(1f),
                ) { app.tela = Tela.CAMERA }
                CartaoMenu(
                    "PROCURAR", "JOGOS NA REDE", R.drawable.ic_rede, Cores.Moss,
                    selo = if (achados == 1) "1 ACHADO" else if (achados > 1) "$achados ACHADOS" else null,
                    modifier = Modifier.weight(1f),
                ) { app.tela = Tela.REDE }
                CartaoMenu(
                    "DIGITAR", "O ENDEREÇO DA TV", R.drawable.ic_teclado, Color(0xFF6A5AA8),
                    modifier = Modifier.weight(1f),
                ) { app.tela = Tela.DIGITAR }
            }
            Spacer(Modifier.height(12.u))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Icone(R.drawable.ic_rede, 16, alpha = if (wifi) 1f else 0.5f)
                Spacer(Modifier.width(6.u))
                Texto(
                    if (wifi) "WI-FI LIGADO" else "SEM WI-FI: LIGUE NA MESMA REDE DO COMPUTADOR",
                    cor = if (wifi) Cores.Moss else Cores.Blood,
                    modifier = Modifier.weight(1f),
                    linhas = 1,
                )
                Texto("APP v${BuildConfig.VERSION_NAME}", cor = Cores.Dim)
            }
        }
        Box(
            Modifier
                .align(Alignment.TopEnd)
                .padding(12.u)
        ) {
            Botao("", icone = R.drawable.ic_engrenagem, altura = 32) { app.tela = Tela.AJUSTES }
        }
    }
}

/** O logo do jogo em escala inteira, no meio da caixa. */
@Composable
fun Logo(modifier: Modifier = Modifier) {
    val m = LocalMedidas.current
    val img = ImageBitmap.imageResource(R.drawable.logo)
    Spacer(
        modifier.drawBehind {
            val s = escalaInteira(img.width.toFloat(), img.height.toFloat(), size.width, size.height, 3, m.k)
            if (s <= 0f) return@drawBehind
            val w = img.width * s
            val h = img.height * s
            desenharPixel(img, ((size.width - w) / 2f).roundToInt().toFloat(), ((size.height - h) / 2f).roundToInt().toFloat(), w, h)
        }
    )
}

/** Recado com um botão (erro de conexão, permissão negada). */
@Composable
fun Faixa(texto: String, botao: String, aoTocar: () -> Unit) {
    val m = LocalMedidas.current
    Row(
        Modifier
            .fillMaxWidth(0.8f)
            .moldura(m, fundo = Color(0xFF3A1A22), luz = Color(0xFF6A2A34), sombra = Color(0xFF1A0A10))
            .padding(horizontal = 12.u, vertical = 6.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.u),
    ) {
        Texto(texto, Modifier.weight(1f), cor = Color(0xFFFFB0A8))
        Botao(botao, altura = 28, aoTocar = aoTocar)
    }
}

/** VOLTAR AO PC-DA-SALA: o último jogo, direto na mesma vaga. */
@Composable
fun BarraVoltar(jogo: JogoSalvo, modifier: Modifier = Modifier, aoTocar: () -> Unit) {
    val m = LocalMedidas.current
    val apertado = remember { mutableStateOf(false) }
    Row(
        modifier
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .moldura(m, fundo = Cores.Verde, luz = Color(0xFF4FB06A), sombra = Color(0xFF1C5A2E))
            .aoTocar(apertado = apertado, acao = aoTocar)
            .padding(horizontal = 12.u, vertical = 6.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.u),
    ) {
        Icone(R.drawable.ic_pc, 32, sombra = true)
        Column(Modifier.weight(1f)) {
            Texto("VOLTAR AO ${jogo.nome.ifEmpty { jogo.host }}", tam = 16, sombra = true, linhas = 1)
            Texto("ÚLTIMO JOGO · ${quando(jogo.quando)}", cor = Color(0xFFCFF5D8), linhas = 1)
        }
        if (jogo.vaga in 1..4) {
            val cor = corVaga(jogo.vaga)
            Box(
                Modifier
                    .moldura(m, fundo = cor, luz = Color.White.copy(alpha = 0.35f), sombra = Color.Black.copy(alpha = 0.35f))
                    .padding(horizontal = 8.u, vertical = 6.u)
            ) {
                Texto("P${jogo.vaga}", tam = 16, cor = Color.White, linha = 16)
            }
        }
    }
}

/** Um dos três cartões grandes do menu: desenho em cima (com brilho), nome e explicação embaixo. */
@Composable
fun CartaoMenu(
    titulo: String,
    sub: String,
    icone: Int,
    brilho: Color,
    modifier: Modifier = Modifier,
    destaque: Boolean = false,
    selo: String? = null,
    aoTocar: () -> Unit,
) {
    val m = LocalMedidas.current
    val apertado = remember { mutableStateOf(false) }
    Column(
        modifier
            .fillMaxHeight()
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .drawBehind { if (destaque) cantos(m, Cores.Brass) }
            .moldura(m, fundo = Color(0xFF2A2448))
            .aoTocar(apertado = apertado, acao = aoTocar)
            .padding(8.u),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .drawBehind {
                    drawRect(Color(0xFF15111F))
                    drawRect(
                        Brush.radialGradient(
                            0f to brilho.copy(alpha = 0.38f), 1f to Color.Transparent,
                            center = center, radius = size.minDimension * 0.85f,
                        )
                    )
                    drawRect(Color.Black.copy(alpha = 0.5f), size = Size(size.width, m.px(2)))
                },
            contentAlignment = Alignment.Center,
        ) {
            Icone(icone, 64, sombra = true)
            if (selo != null) {
                Box(
                    Modifier
                        .align(Alignment.TopEnd)
                        .padding(6.u)
                        .drawBehind { drawRect(Cores.Moss) }
                        .padding(horizontal = 4.u, vertical = 2.u)
                ) {
                    Texto(selo, cor = Cores.Ink, linhas = 1)
                }
            }
        }
        Spacer(Modifier.height(10.u))
        Texto(titulo, tam = 16, sombra = true, alinhar = TextAlign.Center, linhas = 1)
        Spacer(Modifier.height(6.u))
        Texto(sub, cor = Cores.Muted, alinhar = TextAlign.Center, linhas = 1)
        Spacer(Modifier.height(6.u))
    }
}

/** Cantinhos dourados em volta (o cartão que é o caminho mais fácil). */
private fun androidx.compose.ui.graphics.drawscope.DrawScope.cantos(m: Medidas, cor: Color) {
    val f = m.px(8)
    val l = m.px(14)
    val t = m.px(3)
    val x0 = -f
    val y0 = -f
    val x1 = size.width + f
    val y1 = size.height + f
    drawRect(cor, Offset(x0, y0), Size(l, t))
    drawRect(cor, Offset(x0, y0), Size(t, l))
    drawRect(cor, Offset(x1 - l, y0), Size(l, t))
    drawRect(cor, Offset(x1 - t, y0), Size(t, l))
    drawRect(cor, Offset(x0, y1 - t), Size(l, t))
    drawRect(cor, Offset(x0, y1 - l), Size(t, l))
    drawRect(cor, Offset(x1 - l, y1 - t), Size(l, t))
    drawRect(cor, Offset(x1 - t, y1 - l), Size(t, l))
}
