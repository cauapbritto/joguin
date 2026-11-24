package io.github.cauapbritto.soulstrike.controle.telas

import androidx.activity.compose.BackHandler
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.input.clearText
import androidx.compose.foundation.text.input.rememberTextFieldState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.style.TextAlign
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.jogo.Loja
import io.github.cauapbritto.soulstrike.controle.jogo.Me
import io.github.cauapbritto.soulstrike.controle.jogo.Status
import io.github.cauapbritto.soulstrike.controle.rede.Http
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Tag
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.desenharPixel
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.conflate
import kotlinx.coroutines.withContext
import java.util.Locale
import kotlin.math.floor
import kotlin.math.min

// ── computador da Casa ────────────────────────
// A TV manda a tela de dentro do computador em PNG (240 x 126); o toque na cópia vira clique lá.
// Igual ao site: busca de novo quando a versão muda e a cada 1,5 s (o cristal girando).

private val NOMES_DOS_CAMPOS = mapOf("terminal" to "TERMINAL", "url" to "ENDEREÇO", "senha" to "SENHA")

private suspend fun baixarTela(url: String): ImageBitmap? = withContext(Dispatchers.IO) {
    val r = Http.get(url, 3000)
    if (r == null || !r.ok || r.corpo.isEmpty()) return@withContext null
    val opcoes = BitmapFactory.Options().apply {
        inScaled = false
        inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    try {
        BitmapFactory.decodeByteArray(r.corpo, 0, r.corpo.size, opcoes)?.asImageBitmap()
    } catch (e: Exception) {
        null
    }
}

private fun campoTocado(loja: Loja, u: Float, v: Float): String? =
    loja.campos.lastOrNull { u >= it.x && u <= it.x + it.w && v >= it.y && v <= it.y + it.h }?.nome

@Composable
fun TelaComputador(st: Status, me: Me, loja: Loja) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    val densidade = LocalDensity.current
    val focos = LocalFocusManager.current
    val teclado = LocalSoftwareKeyboardController.current
    val campo = rememberTextFieldState()
    val pedirFoco = remember { FocusRequester() }
    var quadro by remember { mutableStateOf<ImageBitmap?>(null) }
    var pediuCampo by remember { mutableStateOf(false) }
    val enviado = remember { mutableStateOf("") }
    val tecladoAberto = tecladoAberto()

    fun pedir(item: String) = canal.pedirLoja(item, false)

    BackHandler { pedir("voltar") }                 // voltar do Android = VOLTAR (na tela inicial, desliga)

    // a cópia da tela: na hora quando a versão muda e de 1,5 em 1,5 s enquanto o computador está aberto
    LaunchedEffect(loja.versao) {
        while (true) {
            baixarTela(canal.urlTela(loja.versao))?.let { quadro = it }
            delay(1500)
        }
    }

    // tocou num campo de texto: a linha de digitar aparece já, sem esperar a TV responder
    LaunchedEffect(loja.digitando) { if (loja.digitando) pediuCampo = false }
    LaunchedEffect(pediuCampo) {
        if (pediuCampo) {
            delay(2500)
            pediuCampo = false
        }
    }
    val digitando = loja.digitando || pediuCampo

    // a TV mostra o que está sendo digitado (no máximo um envio a cada 120 ms)
    LaunchedEffect(campo) {
        snapshotFlow { campo.text.toString() }.conflate().collect { t ->
            if (t != enviado.value) {
                enviado.value = t
                pedir("pc:buf:$t")
            }
            delay(120)
        }
    }

    fun enviarTexto() {
        val t = campo.text.toString()
        pedir("pc:text:$t")
        enviado.value = ""
        campo.clearText()
        if (loja.foco != "terminal") focos.clearFocus()       // no terminal o teclado fica aberto
    }

    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Tag(me.vaga, me.personagem)
            Texto(loja.titulo.ifEmpty { "COMPUTADOR" }, Modifier.weight(1f), tam = 16, sombra = true, linhas = 1)
            Botao("VOLTAR", altura = 32, naHora = true) { pedir("voltar") }
            Botao("FECHAR TUDO", tipo = TipoBotao.VERMELHO, altura = 32, naHora = true) {
                focos.clearFocus()
                pedir("fechar")
            }
        }
        Column(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(start = 12.u, end = 12.u, top = 12.u, bottom = 8.u),
            verticalArrangement = Arrangement.spacedBy(8.u),
        ) {
            if (tecladoAberto && digitando) {
                // com o teclado aberto, só a linha digitada: quem digita olha na TV
                Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    Texto("OLHE NA TV", tam = 16, cor = Cores.Muted, alinhar = TextAlign.Center)
                }
            } else {
                BoxWithConstraints(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    val dica = 14.u
                    val livreW = constraints.maxWidth.toFloat() - m.px(8)
                    val livreH = constraints.maxHeight.toFloat() - with(densidade) { dica.toPx() } - m.px(16)
                    val img = quadro
                    val iw = img?.width?.toFloat() ?: (126f * loja.proporcao)
                    val ih = img?.height?.toFloat() ?: 126f
                    var escala = min(livreW / iw, livreH / ih).coerceAtLeast(0.1f)
                    if (escala >= 3f) escala = floor(escala)             // pixels inteiros: a tela fica nítida
                    val largura = with(densidade) { (iw * escala).toDp() }
                    val altura = with(densidade) { (ih * escala).toDp() }
                    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.u)) {
                        Box(
                            Modifier
                                .size(largura, altura)
                                .drawBehind {
                                    val e = m.px(2)
                                    drawRect(Color.Black, Offset(-2 * e, -2 * e + 3 * e), Size(size.width + 4 * e, size.height + 4 * e))
                                    drawRect(Cores.LineHi, Offset(-2 * e, -2 * e), Size(size.width + 4 * e, size.height + 4 * e))
                                    drawRect(Cores.Edge, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                                    drawRect(Color(0xFF101A2E))
                                    val q = quadro
                                    if (q != null) desenharPixel(q, 0f, 0f, size.width, size.height)
                                }
                                .pointerInput(loja.campos) {
                                    detectTapGestures { p ->
                                        val w = size.width.toFloat()
                                        val h = size.height.toFloat()
                                        if (w <= 0f || h <= 0f) return@detectTapGestures
                                        val u = p.x / w
                                        val v = p.y / h
                                        if (u < 0f || u > 1f || v < 0f || v > 1f) return@detectTapGestures
                                        app.toque()
                                        pedir(String.format(Locale.US, "pc:tap:%.4f,%.4f", u, v))
                                        if (campoTocado(loja, u, v) != null) {      // campo de texto: o teclado sobe no mesmo toque
                                            campo.clearText()
                                            enviado.value = ""
                                            pediuCampo = true
                                        }
                                    }
                                },
                            contentAlignment = Alignment.Center,
                        ) {
                            if (quadro == null) Texto("LIGANDO...", cor = Color(0xFF6E86B8))
                        }
                        Texto(
                            if (digitando) "TOQUE NA LINHA DE BAIXO PARA DIGITAR" else "TOQUE NA TELA PARA CLICAR",
                            cor = Cores.Muted, alinhar = TextAlign.Center, linhas = 1,
                        )
                    }
                }
            }
            if (digitando) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.u)) {
                    Texto(NOMES_DOS_CAMPOS[loja.foco] ?: "", cor = Cores.Brass, linhas = 1)
                    CampoDeTexto(
                        campo, "", borda = Color(0xFF1D3A26), fundo = Color(0xFF06110A), corTexto = Color(0xFF7DFF9A),
                        maiusculas = false, maximo = 70, modifier = Modifier.weight(1f).focusRequester(pedirFoco),
                        senha = loja.foco == "senha",
                    ) { enviarTexto() }
                    Botao("ENVIAR", tipo = TipoBotao.VERDE, altura = 40) { enviarTexto() }
                }
                LaunchedEffect(pediuCampo) {
                    if (pediuCampo) {
                        try {
                            pedirFoco.requestFocus()
                            teclado?.show()
                        } catch (e: IllegalStateException) {
                            // o campo ainda não estava na tela: o próximo toque resolve
                        }
                    }
                }
            }
        }
    }
}
