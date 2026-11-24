package io.github.cauapbritto.soulstrike.controle.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.github.cauapbritto.soulstrike.controle.R
import kotlin.math.roundToInt

/** As cores do controle (as mesmas do site do celular e do jogo). */
object Cores {
    val Ink = Color(0xFF0C0A14)
    val Ink2 = Color(0xFF1B1729)
    val Ink3 = Color(0xFF231E36)
    val Ink4 = Color(0xFF2C2546)
    val Line = Color(0xFF3A3156)
    val LineHi = Color(0xFF4A4170)
    val Lo = Color(0xFF0D0A16)
    val Edge = Color(0xFF050409)
    val Bone = Color(0xFFF4ECD8)
    val Muted = Color(0xFF9A90B8)
    val Dim = Color(0xFF5D5578)
    val Brass = Color(0xFFFFD75A)
    val Moss = Color(0xFF5AD27A)
    val Blood = Color(0xFFFF5A5A)
    val Soul = Color(0xFFC8AAFF)
    val Energy = Color(0xFF6EC8FF)
    val Caco = Color(0xFF8FD6FF)
    val Comum = Color(0xFF8A86A0)
    val Verde = Color(0xFF2F8A4A)
    val Vermelho = Color(0xFF7A2424)
    val Bolso = Color(0xFF0E0B18)
    val Desligado = Color(0xFF221D33)
    val TopoA = Color(0xFF2A2244)
    val TopoB = Color(0xFF1A1530)
    val Papel = Color(0xFFF4ECD8)
    val Tinta = Color(0xFF1A1530)
}

/** A cor de cada jogador: P1 azul, P2 vermelho, P3 verde, P4 laranja. */
fun corVaga(n: Int): Color = when (n) {
    2 -> Color(0xFFFF5A4A)
    3 -> Color(0xFF3CCF8A)
    4 -> Color(0xFFFFB43C)
    else -> Color(0xFF4A8CFF)
}

fun corVagaEscura(n: Int): Color = when (n) {
    2 -> Color(0xFF602220)
    3 -> Color(0xFF1E5448)
    4 -> Color(0xFF68481A)
    else -> Color(0xFF22386A)
}

/** "#f4ecd8" (o jogo manda as cores assim) para Color. */
fun corHex(s: String?, padrao: Color = Cores.Bone): Color {
    val t = s?.trim()?.removePrefix("#") ?: return padrao
    val v = t.toLongOrNull(16) ?: return padrao
    return when (t.length) {
        6 -> Color(0xFF000000L or v)
        8 -> Color(v)
        else -> padrao
    }
}

/** color-mix do CSS: ``parte`` de ``a`` com o resto de ``b``. */
fun mistura(a: Color, parte: Float, b: Color): Color = lerp(b, a, parte)

/** Cinza e mais escuro (o que não dá para comprar). */
fun filtroCinza(brilho: Float): ColorFilter {
    val r = 0.2126f * brilho
    val g = 0.7152f * brilho
    val b = 0.0722f * brilho
    return ColorFilter.colorMatrix(
        ColorMatrix(
            floatArrayOf(
                r, g, b, 0f, 0f,
                r, g, b, 0f, 0f,
                r, g, b, 0f, 0f,
                0f, 0f, 0f, 1f, 0f,
            )
        )
    )
}

/**
 * Medidas em "pixels do jogo". Cada um vale ``k`` pixels da tela (k inteiro, perto da densidade),
 * então a fonte de pixel (feita para 8, 16 e 24) e as bordas ficam nítidas em qualquer celular.
 */
class Medidas(val k: Int, private val densidade: Float, private val escalaFonte: Float) {
    fun dp(n: Number): Dp = (n.toFloat() * k / densidade).dp
    fun sp(n: Number): TextUnit = (n.toFloat() * k / (densidade * escalaFonte)).sp
    fun px(n: Number): Float = n.toFloat() * k

    /** Pixels da tela para pixels do jogo. */
    fun deTela(px: Float): Float = px / k

    companion object {
        fun para(densidade: Float, escalaFonte: Float): Medidas =
            Medidas(maxOf(1, densidade.roundToInt()), densidade, escalaFonte)
    }
}

val LocalMedidas = staticCompositionLocalOf { Medidas(2, 2f, 1f) }

/** 12.u = 12 pixels do jogo. */
val Int.u: Dp
    @Composable @ReadOnlyComposable get() = LocalMedidas.current.dp(this)

val FontePixel = FontFamily(Font(R.font.pixel))

private val LinhaNoMeio = LineHeightStyle(
    alignment = LineHeightStyle.Alignment.Center,
    trim = LineHeightStyle.Trim.None,
)

/** Estilo de texto na fonte do jogo: tamanho 8, 16 ou 24 (sempre nítido). */
@Composable
@ReadOnlyComposable
fun estilo(
    tam: Int = 8,
    cor: Color = Cores.Bone,
    alinhar: TextAlign = TextAlign.Start,
    sombra: Boolean = false,
    linha: Int = 0,
): TextStyle {
    val m = LocalMedidas.current
    val altura = if (linha > 0) linha else when (tam) {
        8 -> 12
        16 -> 20
        else -> tam
    }
    return TextStyle(
        color = cor,
        fontSize = m.sp(tam),
        lineHeight = m.sp(altura),
        fontFamily = FontePixel,
        textAlign = alinhar,
        lineHeightStyle = LinhaNoMeio,
        shadow = if (sombra) Shadow(color = Color.Black, offset = Offset(m.px(2), m.px(2)), blurRadius = 0f) else null,
    )
}
