package io.github.cauapbritto.soulstrike.controle.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.TileMode
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.imageResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import io.github.cauapbritto.soulstrike.controle.LocalApp
import kotlinx.coroutines.delay
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.roundToInt

// ── texto ─────────────────────────────────────

/** Texto na fonte do jogo. Com ``linhas`` = 1, corta com reticências em vez de quebrar. */
@Composable
fun Texto(
    texto: String,
    modifier: Modifier = Modifier,
    tam: Int = 8,
    cor: Color = Cores.Bone,
    alinhar: TextAlign = TextAlign.Start,
    sombra: Boolean = false,
    linhas: Int = Int.MAX_VALUE,
    linha: Int = 0,
) {
    BasicText(
        text = texto,
        modifier = modifier,
        style = estilo(tam, cor, alinhar, sombra, linha),
        overflow = if (linhas == Int.MAX_VALUE) TextOverflow.Clip else TextOverflow.Ellipsis,
        softWrap = linhas != 1,
        maxLines = linhas,
    )
}

// ── fundo, molduras e linhas de TV ────────────

/** O degradê roxo do fundo (o mesmo do site do celular). */
fun Modifier.fundoDoJogo(): Modifier = drawBehind {
    drawRect(
        Brush.radialGradient(
            0f to Color(0xFF241D3C), 0.55f to Color(0xFF120F1E), 1f to Color(0xFF08070D),
            center = Offset(size.width / 2f, 0f),
            radius = max(size.width, size.height) * 0.9f,
        )
    )
}

/** TV de tubo: linhas finas e cantos escuros por cima de tudo (não pega toque). */
fun Modifier.linhasDeTv(m: Medidas): Modifier = drawWithContent {
    drawContent()
    val passo = m.px(3)
    val risco = Color(0x29000000)
    drawRect(
        Brush.verticalGradient(
            0f to risco, (1f / 3f) to risco, (1f / 3f) to Color.Transparent, 1f to Color.Transparent,
            startY = 0f, endY = passo, tileMode = TileMode.Repeated,
        )
    )
    drawRect(
        Brush.radialGradient(
            0.5f to Color.Transparent, 1f to Color(0x8C000000),
            center = center, radius = max(size.width, size.height) * 0.62f,
        )
    )
}

/**
 * Moldura de pixel: borda escura por fora, luz em cima e à esquerda, sombra embaixo e à direita.
 * A borda de fora fica fora do tamanho (como o box-shadow do site).
 */
fun Modifier.moldura(
    m: Medidas,
    fundo: Color = Cores.Ink2,
    luz: Color = Cores.LineHi,
    sombra: Color = Cores.Lo,
    borda: Color = Cores.Edge,
    grossura: Int = 2,
    fora: Int = 2,
    anel: Color? = null,
): Modifier = drawBehind {
    val b = m.px(grossura)
    val f = m.px(fora)
    if (anel != null) {
        val a = f + m.px(2)
        drawRect(anel, topLeft = Offset(-a, -a), size = Size(size.width + 2 * a, size.height + 2 * a))
    }
    if (f > 0f) drawRect(borda, topLeft = Offset(-f, -f), size = Size(size.width + 2 * f, size.height + 2 * f))
    drawRect(fundo)
    if (b > 0f) {
        drawRect(luz, size = Size(size.width, b))
        drawRect(luz, size = Size(b, size.height))
        drawRect(sombra, topLeft = Offset(0f, size.height - b), size = Size(size.width, b))
        drawRect(sombra, topLeft = Offset(size.width - b, 0f), size = Size(b, size.height))
    }
}

/** Contorno tracejado (ajustes do controle: o que dá para arrastar). */
fun DrawScope.tracejado(m: Medidas, cor: Color, x: Float, y: Float, w: Float, h: Float) {
    val t = m.px(2)
    val passo = m.px(6)
    var p = 0f
    while (p < w) {
        val l = minOf(m.px(3), w - p)
        drawRect(cor, Offset(x + p, y), Size(l, t))
        drawRect(cor, Offset(x + p, y + h - t), Size(l, t))
        p += passo
    }
    p = 0f
    while (p < h) {
        val l = minOf(m.px(3), h - p)
        drawRect(cor, Offset(x, y + p), Size(t, l))
        drawRect(cor, Offset(x + w - t, y + p), Size(t, l))
        p += passo
    }
}

// ── toque ─────────────────────────────────────

/**
 * Toque de botão: vibra um tiquinho (se ligado) e chama ``acao`` ao soltar dentro dele, ou na
 * hora do toque com ``naHora`` (botões do jogo, como no site).
 */
@Composable
fun Modifier.aoTocar(
    ativo: Boolean = true,
    naHora: Boolean = false,
    apertado: MutableState<Boolean>? = null,
    acao: () -> Unit,
): Modifier {
    val app = LocalApp.current
    val atual = rememberUpdatedState(acao)
    return this.pointerInput(ativo, naHora) {
        if (!ativo) return@pointerInput
        awaitEachGesture {
            val toque = awaitFirstDown(requireUnconsumed = false)
            toque.consume()
            apertado?.value = true
            app.toque()
            if (naHora) atual.value()
            val solto = waitForUpOrCancellation()
            apertado?.value = false
            if (solto != null) {
                solto.consume()
                if (!naHora) atual.value()
            }
        }
    }
}

/** Liga e desliga a cada ``periodo`` ms (piscar). */
@Composable
fun piscando(periodo: Long = 300L): State<Boolean> {
    val st = remember { mutableStateOf(false) }
    LaunchedEffect(periodo) {
        while (true) {
            delay(periodo)
            st.value = !st.value
        }
    }
    return st
}

// ── botões ────────────────────────────────────

enum class TipoBotao { NORMAL, PRINCIPAL, VERDE, VERMELHO, DOURADO }

/** Botão de fliperama (o .btn do site): luz em cima, faixa escura embaixo e afunda ao apertar. */
@Composable
fun Botao(
    texto: String,
    modifier: Modifier = Modifier,
    tipo: TipoBotao = TipoBotao.NORMAL,
    tam: Int = 8,
    sub: String? = null,
    icone: Int? = null,
    ativo: Boolean = true,
    ligado: Boolean = false,
    naHora: Boolean = false,
    vaga: Int = 1,
    altura: Int = 40,
    largo: Boolean = false,
    aoTocar: () -> Unit,
) {
    val m = LocalMedidas.current
    val apertado = remember { mutableStateOf(false) }
    val fundo = when {
        !ativo -> Cores.Desligado
        ligado -> Color(0xFF2D4A36)
        tipo == TipoBotao.PRINCIPAL -> corVagaEscura(vaga)
        tipo == TipoBotao.VERDE -> Cores.Verde
        tipo == TipoBotao.VERMELHO -> Cores.Vermelho
        tipo == TipoBotao.DOURADO -> Cores.Brass
        else -> Cores.Ink4
    }
    val corTexto = when {
        !ativo -> Cores.Dim
        ligado -> Cores.Moss
        tipo == TipoBotao.VERDE || tipo == TipoBotao.VERMELHO -> Color.White
        tipo == TipoBotao.DOURADO -> Cores.Tinta
        else -> Cores.Bone
    }
    val anel = if (tipo == TipoBotao.PRINCIPAL && ativo) corVaga(vaga) else null
    Box(
        modifier
            .heightIn(min = altura.u)
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .drawBehind {
                val e = m.px(2)
                if (anel != null) {
                    val a = m.px(4)
                    drawRect(anel, Offset(-a, -a), Size(size.width + 2 * a, size.height + 2 * a))
                }
                drawRect(Cores.Edge, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(fundo)
                val luz = Color.White.copy(alpha = if (apertado.value) 0.1f else if (anel != null) 0.22f else 0.18f)
                drawRect(luz, size = Size(size.width, e))
                drawRect(luz, size = Size(e, size.height))
                val faixa = m.px(if (apertado.value) 2 else 6)
                drawRect(Color.Black.copy(alpha = 0.35f), Offset(0f, size.height - faixa), Size(size.width, faixa))
            }
            .aoTocar(ativo = ativo, naHora = naHora, apertado = apertado, acao = aoTocar)
            .padding(start = 12.u, end = 12.u, top = 2.u, bottom = 6.u),
        contentAlignment = Alignment.Center,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.u, Alignment.CenterHorizontally),
            modifier = if (largo) Modifier.fillMaxWidth() else Modifier,
        ) {
            if (icone != null) Icone(icone, 16, filtro = if (ativo) null else filtroCinza(0.6f))
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Texto(texto, tam = tam, cor = corTexto, alinhar = TextAlign.Center, linhas = 1)
                if (sub != null) {
                    Texto(
                        sub, tam = 8, alinhar = TextAlign.Center, linhas = 1,
                        cor = if (tipo == TipoBotao.VERDE) Color(0xFFCFF5D8) else Cores.Muted,
                    )
                }
            }
        }
    }
}

// ── desenhos de pixel ─────────────────────────

/** Desenha a imagem sem borrar (pixel duro). */
fun DrawScope.desenharPixel(
    img: ImageBitmap,
    x: Float,
    y: Float,
    w: Float,
    h: Float,
    alpha: Float = 1f,
    filtro: ColorFilter? = null,
) {
    drawImage(
        image = img,
        srcOffset = IntOffset.Zero,
        srcSize = IntSize(img.width, img.height),
        dstOffset = IntOffset(x.roundToInt(), y.roundToInt()),
        dstSize = IntSize(w.roundToInt().coerceAtLeast(1), h.roundToInt().coerceAtLeast(1)),
        alpha = alpha,
        colorFilter = filtro,
        filterQuality = FilterQuality.None,
    )
}

/**
 * Escala inteira que cabe na caixa: 1x, 2x, 3x... em pixels do jogo (no máximo ``max``); grande
 * demais, reduz por um divisor inteiro. Igual ao fitIcon do site.
 */
fun escalaInteira(nw: Float, nh: Float, bw: Float, bh: Float, max: Int, k: Int): Float {
    if (nw <= 0f || nh <= 0f || bw <= 0f || bh <= 0f) return 0f
    val s = minOf(bw / nw, bh / nh, (max * k).toFloat())
    return when {
        s >= k -> floor(s / k) * k
        s >= 1f -> floor(s)
        else -> 1f / ceil(1f / s)
    }
}

/** Desenha com sombra, aura (brilho da raridade) e silhueta, como os filtros do site. */
fun DrawScope.desenharComEfeito(
    m: Medidas,
    img: ImageBitmap,
    x: Float,
    y: Float,
    w: Float,
    h: Float,
    sombra: Boolean = true,
    aura: Color? = null,
    silhueta: Boolean = false,
    filtro: ColorFilter? = null,
    alpha: Float = 1f,
) {
    val um = m.px(1)
    if (aura != null) {
        val tinta = ColorFilter.tint(aura.copy(alpha = 0.55f), BlendMode.SrcIn)
        for ((dx, dy) in AURA) desenharPixel(img, x + dx * um, y + dy * um, w, h, alpha, tinta)
    }
    if (sombra && !silhueta) {
        val s = m.px(2)
        desenharPixel(img, x + s, y + s, w, h, alpha, ColorFilter.tint(Color(0x73000000), BlendMode.SrcIn))
    }
    val f = if (silhueta) ColorFilter.tint(Color.Black, BlendMode.SrcIn) else filtro
    desenharPixel(img, x, y, w, h, alpha, f)
}

private val AURA = listOf(
    -1 to 0, 1 to 0, 0 to -1, 0 to 1, -1 to -1, 1 to -1, -1 to 1, 1 to 1, -2 to 0, 2 to 0, 0 to -2, 0 to 2,
)

/**
 * Desenho do jogo encaixado na caixa em escala inteira (heróis, armas, skins, pets). ``div`` volta
 * ao pixel de verdade quando a imagem chega ampliada (os retratos das skins vêm 3x).
 */
@Composable
fun ImagemPixel(
    img: ImageBitmap?,
    modifier: Modifier = Modifier,
    max: Int = 4,
    pad: Int = 8,
    div: Int = 1,
    sombra: Boolean = true,
    aura: Color? = null,
    silhueta: Boolean = false,
    filtro: ColorFilter? = null,
    embaixo: Boolean = false,
    alpha: Float = 1f,
) {
    val m = LocalMedidas.current
    Spacer(
        modifier.drawBehind {
            if (img == null) return@drawBehind
            val nw = img.width / div.toFloat()
            val nh = img.height / div.toFloat()
            val s = escalaInteira(nw, nh, size.width - m.px(pad), size.height - m.px(pad), max, m.k)
            if (s <= 0f) return@drawBehind
            val w = nw * s
            val h = nh * s
            val x = ((size.width - w) / 2f).roundToInt().toFloat()
            val y = if (embaixo) size.height - h - m.px(pad) / 2f else ((size.height - h) / 2f).roundToInt().toFloat()
            desenharComEfeito(m, img, x, y, w, h, sombra, aura, silhueta, filtro, alpha)
        }
    )
}

/** Ícone do app (16x16) em tamanho múltiplo de 16: 16, 32, 48... */
@Composable
fun Icone(
    res: Int,
    tam: Int = 16,
    modifier: Modifier = Modifier,
    filtro: ColorFilter? = null,
    alpha: Float = 1f,
    sombra: Boolean = false,
) {
    val img = ImageBitmap.imageResource(res)
    val m = LocalMedidas.current
    Canvas(modifier.size(tam.u)) {
        if (sombra) {
            val s = m.px(2)
            desenharPixel(img, s, s, size.width, size.height, alpha, ColorFilter.tint(Color(0x99000000), BlendMode.SrcIn))
        }
        desenharPixel(img, 0f, 0f, size.width, size.height, alpha, filtro)
    }
}

// ── peças comuns das telas ────────────────────

/** Faixa de cima das telas (seleção, loja, computador...). */
@Composable
fun Cabecalho(modifier: Modifier = Modifier, conteudo: @Composable RowScope.() -> Unit) {
    val m = LocalMedidas.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .drawBehind {
                drawRect(Brush.verticalGradient(listOf(Cores.TopoA, Cores.TopoB)))
                drawRect(Cores.Edge, Offset(0f, size.height), Size(size.width, m.px(2)))
                drawRect(Color.Black.copy(alpha = 0.35f), Offset(0f, size.height + m.px(2)), Size(size.width, m.px(2)))
            }
            .padding(horizontal = 12.u, vertical = 6.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.u),
        content = conteudo,
    )
}

/** Etiqueta do jogador: rostinho do herói + P1 na cor da vaga. */
@Composable
fun Tag(vaga: Int, personagem: Int?, grande: Boolean = false, modifier: Modifier = Modifier) {
    val m = LocalMedidas.current
    val face = imagemDoJogo(personagem?.takeIf { it >= 0 }?.let { "/sprite/$it.png" })
    val cor = corVaga(vaga)
    val lado = if (grande) 36 else 24
    val largura = if (grande) 75 else 50
    Row(
        modifier
            .height((if (grande) 40 else 28).u)
            .drawBehind {
                val e = m.px(2)
                drawRect(Cores.Edge, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(cor)
                drawRect(Color.White.copy(alpha = 0.35f), size = Size(size.width, e))
                drawRect(Color.White.copy(alpha = 0.35f), size = Size(e, size.height))
                drawRect(Color.Black.copy(alpha = 0.35f), Offset(0f, size.height - e), Size(size.width, e))
                drawRect(Color.Black.copy(alpha = 0.35f), Offset(size.width - e, 0f), Size(e, size.height))
            }
            .padding(start = 2.u, end = 6.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.u),
    ) {
        Spacer(
            Modifier
                .size(lado.u)
                .drawBehind {
                    drawRect(Color.Black.copy(alpha = 0.25f))
                    val img = face ?: return@drawBehind
                    val s = maxOf(1f, (m.px(largura) / img.width).roundToInt().toFloat())
                    val w = img.width * s
                    val h = img.height * s
                    clipRect {
                        desenharPixel(img, ((size.width - w) / 2f).roundToInt().toFloat(), 0f, w, h)
                    }
                }
        )
        Texto("P$vaga", tam = 16, cor = Color.White, linha = 16)
    }
}

/** Pílula de saldo (almas, energia, cacos). */
@Composable
fun Pilula(icone: Int, texto: String, cor: Color, modifier: Modifier = Modifier, unidade: String? = null) {
    val m = LocalMedidas.current
    Row(
        modifier
            .height(24.u)
            .drawBehind {
                val e = m.px(2)
                drawRect(Cores.Line, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(Cores.Bolso)
                drawRect(Color.Black, size = Size(size.width, e))
                drawRect(Color.Black, size = Size(e, size.height))
            }
            .padding(start = 4.u, end = 8.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.u),
    ) {
        Icone(icone, 16)
        Texto(texto, tam = 16, cor = cor, linha = 16, linhas = 1)
        if (unidade != null) Texto(unidade, cor = Cores.Muted, linhas = 1)
    }
}

/** Barra em 10 quadradinhos: o que tem em branco e o ganho piscando em verde. */
@Composable
fun Segmentos(antes: Float, depois: Float?, max: Float, modifier: Modifier = Modifier) {
    val m = LocalMedidas.current
    val pisca by piscando(300L)
    val on = (antes / max * 10f).roundToInt().coerceIn(0, 10)
    var sobe = if (depois != null) ((depois / max * 10f).roundToInt().coerceIn(0, 10) - on).coerceAtLeast(0) else 0
    if (depois != null && depois > antes && sobe == 0 && on < 10) sobe = 1
    Spacer(
        modifier
            .height(8.u)
            .drawBehind {
                val gap = m.px(2)
                val w = (size.width - gap * 9) / 10f
                for (i in 0 until 10) {
                    val cor = when {
                        i < on -> Cores.Bone
                        i < on + sobe -> if (pisca) Cores.Moss.copy(alpha = 0.35f) else Cores.Moss
                        else -> Color(0xFF2D2742)
                    }
                    drawRect(cor, Offset(i * (w + gap), 0f), Size(w, size.height))
                }
            }
    )
}

/** Quadradinhos de nível do ferreiro (+1, +2, +3). */
@Composable
fun Niveis(nivel: Int, modifier: Modifier = Modifier) {
    val m = LocalMedidas.current
    Spacer(
        modifier
            .size(22.u, 7.u)
            .drawBehind {
                for (i in 0 until 3) {
                    val x = i * m.px(8)
                    drawRect(Color.Black, Offset(x + m.px(1), m.px(1)), Size(m.px(6), m.px(6)))
                    drawRect(if (i < nivel) Cores.Brass else Color(0xFF2D2742), Offset(x, 0f), Size(m.px(6), m.px(6)))
                }
            }
    )
}

/** Uma caixinha escura com moldura (painel do site). */
@Composable
fun Painel(
    modifier: Modifier = Modifier,
    fundo: Color = Cores.Ink2,
    conteudo: @Composable () -> Unit,
) {
    val m = LocalMedidas.current
    Box(modifier.moldura(m, fundo = fundo)) { conteudo() }
}
