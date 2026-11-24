package io.github.cauapbritto.soulstrike.controle.telas

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.input.clearText
import androidx.compose.foundation.text.input.rememberTextFieldState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.atualizar.Atualizador
import io.github.cauapbritto.soulstrike.controle.jogo.Caderno
import io.github.cauapbritto.soulstrike.controle.jogo.Chamada
import io.github.cauapbritto.soulstrike.controle.jogo.MAX_APELIDO
import io.github.cauapbritto.soulstrike.controle.jogo.MapaJogo
import io.github.cauapbritto.soulstrike.controle.jogo.Resumo
import io.github.cauapbritto.soulstrike.controle.jogo.limparApelido
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.corHex
import io.github.cauapbritto.soulstrike.controle.ui.corVaga
import io.github.cauapbritto.soulstrike.controle.ui.estilo
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.piscando
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlinx.coroutines.delay
import kotlin.math.min
import kotlin.math.roundToInt

/*
 * As novidades do app da v1.60.0 que aparecem em mais de uma tela: reações rápidas, apelido na TV,
 * resumo da partida, o aviso de app novo (ATUALIZAR) e o MAPA com o CADERNO DE SEGREDOS.
 */

// ── reações rápidas ───────────────────────────

/** Uma reação: a chave que o jogo conhece, o nome no botão e o desenho (o mesmo do balão da TV). */
data class Reacao(val chave: String, val rotulo: String, val icone: Int)

val REACOES = listOf(
    Reacao("gg", "GG", R.drawable.r_gg),
    Reacao("kkk", "KKKK", R.drawable.r_kkk),
    Reacao("vem", "VEM!", R.drawable.r_vem),
    Reacao("palmas", "PALMAS", R.drawable.r_palmas),
)

/** As 4 reações com nome (espera e resultado). O balão aparece na TV com um somzinho. */
@Composable
fun BotoesDeReacao(modifier: Modifier = Modifier, altura: Int = 40, aoReagir: () -> Unit = {}) {
    val canal = LocalApp.current.canal
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(8.u), verticalAlignment = Alignment.CenterVertically) {
        for (r in REACOES) {
            Botao(r.rotulo, icone = r.icone, altura = altura, naHora = true) {
                canal.reagir(r.chave)
                aoReagir()
            }
        }
    }
}

/** Só os desenhos, pequenos (a barra de cima da escolha de personagem). */
@Composable
fun IconesDeReacao(modifier: Modifier = Modifier) {
    val canal = LocalApp.current.canal
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(6.u), verticalAlignment = Alignment.CenterVertically) {
        for (r in REACOES) {
            Botao("", icone = r.icone, altura = 28, naHora = true) { canal.reagir(r.chave) }
        }
    }
}

/** O balão de reações do controle: abre pelo botão da barra de cima e fecha sozinho. */
@Composable
fun PainelDeReacoes(aoFechar: () -> Unit) {
    val m = LocalMedidas.current
    LaunchedEffect(Unit) {
        delay(6000)
        aoFechar()
    }
    Column(
        Modifier
            .moldura(m, fundo = Color(0xFF141026))
            .bloquearToques()
            .padding(8.u),
        verticalArrangement = Arrangement.spacedBy(6.u),
    ) {
        Texto("APARECE EM CIMA DO SEU BONECO NA TV", cor = Cores.Brass, linhas = 1)
        BotoesDeReacao(altura = 36) { aoFechar() }
    }
}

// ── o app fechou sozinho ──────────────────────

/** Na abertura depois de um erro: o texto do erro, COPIAR (para mandar) e CONTINUAR. */
@Composable
fun TelaErro(texto: String, aoContinuar: () -> Unit) {
    val m = LocalMedidas.current
    val ctx = LocalContext.current
    var copiado by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Texto("O APP FECHOU SOZINHO DA ÚLTIMA VEZ", tam = 16, cor = Cores.Brass, sombra = true, linhas = 1)
        }
        Row(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.u, vertical = 10.u),
            horizontalArrangement = Arrangement.spacedBy(12.u),
        ) {
            Column(
                Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .moldura(m, fundo = Cores.Bolso)
                    .verticalScroll(rememberScrollState())
                    .padding(8.u),
            ) {
                Texto(texto, cor = Cores.Muted)
            }
            Column(Modifier.width(200.u), verticalArrangement = Arrangement.spacedBy(10.u)) {
                Texto("COPIE ESTE TEXTO E MANDE PARA QUEM FAZ O JOGO: COM ELE DÁ PARA CONSERTAR.", cor = Cores.Bone)
                Botao(if (copiado) "COPIADO!" else "COPIAR", Modifier.fillMaxWidth(), altura = 36, largo = true) {
                    try {
                        val cb = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        cb.setPrimaryClip(ClipData.newPlainText("erro do Soul Strike Controle", texto))
                        copiado = true
                    } catch (e: Exception) {
                        // sem área de transferência: dá para tirar print
                    }
                }
                Botao("CONTINUAR", Modifier.fillMaxWidth(), tipo = TipoBotao.VERDE, altura = 36, largo = true) { aoContinuar() }
            }
        }
    }
}

// ── frases para a equipe ──────────────────────

/** Uma frase do botão EQUIPE: a chave que o jogo conhece e o texto (o mesmo do balão da TV). */
data class Frase(val chave: String, val texto: String)

val FRASES = listOf(
    Frase("passa", "PASSA!"),
    Frase("chuta", "CHUTA!"),
    Frase("ajuda", "AJUDA!"),
    Frase("frente", "VOU NA FRENTE"),
    Frase("cuidado", "CUIDADO!"),
    Frase("aqui", "VEM PRA CÁ"),
)

fun textoDaFrase(chave: String): String = FRASES.firstOrNull { it.chave == chave }?.texto ?: chave.uppercase()

/** O balão do botão EQUIPE: 6 frases prontas; só o seu time recebe (e o celular deles vibra). */
@Composable
fun PainelDaEquipe(aoFechar: () -> Unit) {
    val m = LocalMedidas.current
    val canal = LocalApp.current.canal
    LaunchedEffect(Unit) {
        delay(6000)
        aoFechar()
    }
    Column(
        Modifier
            .moldura(m, fundo = Color(0xFF141026))
            .bloquearToques()
            .padding(8.u),
        verticalArrangement = Arrangement.spacedBy(6.u),
    ) {
        Texto("SÓ O SEU TIME RECEBE NO CELULAR (E VÊ NA TV)", cor = Cores.Brass, linhas = 1)
        for (linha in FRASES.chunked(3)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.u)) {
                for (f in linha) {
                    Botao(f.texto, Modifier.width(118.u), altura = 36, naHora = true) {
                        canal.chamarEquipe(f.chave)
                        aoFechar()
                    }
                }
            }
        }
    }
}

/** O recado de um colega no alto do controle ("P2: PASSA!"), enquanto ele estiver no ar. */
@Composable
fun AvisoDaEquipe(chamadas: List<Chamada>, modifier: Modifier = Modifier) {
    val c = chamadas.lastOrNull() ?: return
    val m = LocalMedidas.current
    val cor = corVaga(c.de)
    Row(
        modifier
            .moldura(m, fundo = Color(0xFF141026), luz = cor, sombra = Color.Black)
            .padding(horizontal = 12.u, vertical = 6.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.u),
    ) {
        Texto(c.rotulo.ifEmpty { "P${c.de}" }, cor = cor, linhas = 1, sombra = true)
        Texto(textoDaFrase(c.tipo), tam = 16, cor = Cores.Bone, linhas = 1, sombra = true)
    }
}

// ── apelido na TV ─────────────────────────────

/** "NA TV: CAUÃ [MUDAR]": o nome que a TV mostra no lugar de P1. */
@Composable
fun LinhaApelido(vaga: Int, modifier: Modifier = Modifier, aoMudar: () -> Unit) {
    val app = LocalApp.current
    val nome = app.apelido.ifEmpty { if (vaga > 0) "P$vaga" else "P1, P2..." }
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.u)) {
        Texto("NA TV:", cor = Cores.Muted, linhas = 1)
        Texto(nome, tam = 16, cor = if (vaga > 0) corVaga(vaga) else Cores.Bone, linhas = 1, sombra = true)
        Botao(if (app.apelido.isEmpty()) "ESCOLHER APELIDO" else "MUDAR", altura = 28) { aoMudar() }
    }
}

/** A caixa de escrever o apelido (até 10 letras; a prévia mostra como fica na TV). */
@Composable
fun EditarApelido(aoFechar: () -> Unit) {
    val app = LocalApp.current
    val m = LocalMedidas.current
    val campo = rememberTextFieldState(app.apelido)
    val pedirFoco = remember { FocusRequester() }
    val teclado = LocalSoftwareKeyboardController.current

    fun fechar() {
        teclado?.hide()
        aoFechar()
    }

    fun salvar() {
        app.mudarApelido(campo.text.toString())
        fechar()
    }

    BackHandler { fechar() }
    LaunchedEffect(Unit) {
        try {
            pedirFoco.requestFocus()
            teclado?.show()
        } catch (e: IllegalStateException) {
            // o campo ainda não estava na tela: o toque nele resolve
        }
    }
    Sobreposicao {
        Column(
            Modifier
                .widthIn(max = 480.u)
                .moldura(m, fundo = Cores.Ink2)
                .padding(16.u),
            verticalArrangement = Arrangement.spacedBy(10.u),
        ) {
            Texto("SEU APELIDO NA TV", tam = 16, cor = Cores.Brass, sombra = true)
            Texto(
                "ATÉ $MAX_APELIDO LETRAS. A TV MOSTRA NO LUGAR DE P1: NO LOBBY, NA ESCOLHA DE PERSONAGEM E EM CIMA DO BONECO.",
                cor = Cores.Muted,
            )
            CampoDeTexto(
                campo, "EX.: CAUÃ", borda = Cores.LineHi, fundo = Cores.Bolso, corTexto = Cores.Bone,
                maiusculas = true, maximo = MAX_APELIDO + 4, modifier = Modifier.focusRequester(pedirFoco),
                textoLivre = true,
            ) { salvar() }
            val previa = limparApelido(campo.text.toString())
            Texto(
                if (previa.isEmpty()) "SEM APELIDO: A TV MOSTRA P1, P2..." else "NA TV VAI APARECER: $previa",
                cor = Cores.Moss, linhas = 1,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.u)) {
                Botao("SEM APELIDO", Modifier.weight(1f), altura = 36) { campo.clearText() }
                Botao("CANCELAR", Modifier.weight(1f), altura = 36) { fechar() }
                Botao("SALVAR", Modifier.weight(1f), tipo = TipoBotao.VERDE, altura = 36) { salvar() }
            }
        }
    }
}

// ── resumo da partida ─────────────────────────

/** Os números de quem está com este celular (gols, pontos, dano, almas), o placar e o DESTAQUE. */
@Composable
fun CartaoResumo(r: Resumo, vaga: Int, modifier: Modifier = Modifier) {
    val m = LocalMedidas.current
    val cor = corHex(r.cor, Cores.Brass)
    val eu = r.jogadores[vaga]
    Column(
        modifier
            .widthIn(min = 300.u, max = 520.u)
            .moldura(m, fundo = Cores.Ink2)
            .drawBehind { drawRect(cor, size = Size(size.width, m.px(4))) }
            .padding(start = 14.u, end = 14.u, top = 14.u, bottom = 12.u),
        verticalArrangement = Arrangement.spacedBy(7.u),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.u)) {
            Texto(r.titulo, Modifier.weight(1f), tam = 16, cor = cor, sombra = true, linhas = 1)
            r.placar?.let { Texto(it, tam = 16, cor = Cores.Bone, linhas = 1, sombra = true) }
        }
        if (eu != null) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.u)) {
                Texto(listOf(eu.rotulo, eu.heroi).filter { it.isNotEmpty() }.joinToString(" · "), cor = corVaga(vaga), linhas = 1)
                when (eu.venceu) {
                    true -> Selo("VENCEU", Cores.Moss)
                    false -> Selo("PERDEU", Cores.Blood)
                    null -> {}
                }
            }
            for ((rotulo, valor) in eu.linhas) LinhaDoResumo(rotulo, valor)
        } else {
            for ((rotulo, valor) in r.linhas) LinhaDoResumo(rotulo, valor)
        }
        val d = r.destaque
        if (d != null) {
            val souEu = vaga > 0 && d.vaga == vaga
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.u)) {
                Selo("DESTAQUE", Cores.Brass)
                Texto(
                    listOf(d.rotulo, d.heroi).filter { it.isNotEmpty() }.joinToString(" · ") + if (souEu) " (VOCÊ!)" else "",
                    cor = if (souEu) Cores.Moss else Cores.Bone, linhas = 1,
                )
            }
        }
        for (rec in r.recordes) Texto("NOVO RECORDE: $rec", cor = Cores.Moss)
    }
}

@Composable
private fun LinhaDoResumo(rotulo: String, valor: String) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Texto(rotulo, Modifier.weight(1f), cor = Cores.Muted, linhas = 1)
        Texto(valor, tam = 16, cor = Cores.Bone, linhas = 1)
    }
}

@Composable
private fun Selo(texto: String, cor: Color) {
    Box(
        Modifier
            .drawBehind { drawRect(cor) }
            .padding(horizontal = 4.u, vertical = 2.u)
    ) {
        Texto(texto, cor = Cores.Ink, linhas = 1)
    }
}

// ── app novo (ATUALIZAR) ──────────────────────

/** "TEM APP NOVO": o jogo (ou o GitHub) está numa versão mais nova que o app. */
@Composable
fun FaixaAtualizar(versao: String?, modifier: Modifier = Modifier) {
    val app = LocalApp.current
    val at = app.atualizador
    val m = LocalMedidas.current
    if (versao == null || (!at.maisNova(versao) && at.fase == Atualizador.Fase.PARADO)) return
    val texto = when (at.fase) {
        Atualizador.Fase.PROCURANDO -> "PROCURANDO..."
        Atualizador.Fase.BAIXANDO ->
            if (at.progresso >= 0f) "BAIXANDO... ${(at.progresso * 100).roundToInt()}%" else "BAIXANDO..."
        Atualizador.Fase.INSTALANDO -> "ABRINDO O INSTALADOR DO ANDROID: CONFIRME LÁ"
        Atualizador.Fase.ERRO -> at.recado
        Atualizador.Fase.PARADO ->
            if (!at.licenca) "O ANDROID PEDE UMA LICENÇA SÓ NA PRIMEIRA VEZ: TOQUE EM PERMITIR E LIGUE \"PERMITIR DESTA FONTE\""
            else "O APP BAIXA DO GITHUB E O ANDROID INSTALA POR CIMA. SEUS AJUSTES FICAM."
    }
    Column(
        modifier
            .widthIn(max = 520.u)
            .moldura(m, fundo = Color(0xFF16301F), luz = Color(0xFF2F6A43), sombra = Color(0xFF0A1A10))
            .padding(horizontal = 12.u, vertical = 8.u),
        verticalArrangement = Arrangement.spacedBy(6.u),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.u)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.u)) {
                Texto("TEM APP NOVO: v$versao (ESTE É v${at.versaoApp})", cor = Cores.Moss, linhas = 1)
                Texto(texto, cor = if (at.fase == Atualizador.Fase.ERRO) Color(0xFFFFB0A8) else Cores.Muted)
            }
            if (!at.ocupado) {
                if (!at.licenca) {
                    Botao("PERMITIR", tipo = TipoBotao.DOURADO, altura = 32) { at.pedirLicenca() }
                } else {
                    Botao(if (at.fase == Atualizador.Fase.ERRO) "TENTAR DE NOVO" else "ATUALIZAR", tipo = TipoBotao.VERDE, altura = 32) {
                        at.atualizar(versao)
                    }
                }
            }
        }
        if (at.fase == Atualizador.Fase.BAIXANDO) {
            val p = at.progresso
            Spacer(
                Modifier
                    .fillMaxWidth()
                    .height(6.u)
                    .drawBehind {
                        drawRect(Color(0xFF0A1A10))
                        if (p >= 0f) drawRect(Cores.Moss, size = Size(size.width * p.coerceIn(0f, 1f), size.height))
                    }
            )
        }
    }
}

// ── MAPA e CADERNO DE SEGREDOS ────────────────

/**
 * O MAPA da partida no celular (fase da campanha ou Casa): a TV continua, o boneco fica parado.
 * O mapa chega de 0,6 em 0,6 s; o caderno, quando a aba abre.
 */
@Composable
fun TelaMapa(vaga: Int, aoFechar: () -> Unit) {
    val canal = LocalApp.current.canal
    val m = LocalMedidas.current
    var aba by remember { mutableStateOf("mapa") }
    var mapa by remember { mutableStateOf<MapaJogo?>(null) }
    var falhas by remember { mutableIntStateOf(0) }
    var caderno by remember { mutableStateOf<Caderno?>(null) }
    var cadernoFalhou by remember { mutableStateOf(false) }
    var pedidoCaderno by remember { mutableIntStateOf(0) }
    BackHandler { aoFechar() }
    LaunchedEffect(Unit) {
        while (true) {
            val novo = canal.buscarMapa()
            if (novo != null) {
                mapa = novo
                falhas = 0
            } else {
                falhas += 1
            }
            delay(600)
        }
    }
    LaunchedEffect(aba, pedidoCaderno) {
        if (aba == "caderno" && caderno == null) {
            cadernoFalhou = false
            caderno = canal.buscarCaderno()
            cadernoFalhou = caderno == null
        }
    }
    Box(
        Modifier
            .fillMaxSize()
            .drawBehind { drawRect(Color(0xF20C0A14)) }
            .bloquearToques()
    ) {
        Column(Modifier.fillMaxSize()) {
            Cabecalho {
                Botao("VOLTAR", icone = R.drawable.ic_voltar, altura = 28) { aoFechar() }
                Botao("MAPA", altura = 28, tipo = if (aba == "mapa") TipoBotao.DOURADO else TipoBotao.NORMAL) { aba = "mapa" }
                Botao("CADERNO", altura = 28, tipo = if (aba == "caderno") TipoBotao.DOURADO else TipoBotao.NORMAL) { aba = "caderno" }
                Spacer(Modifier.weight(1f))
                Texto("A TV NÃO PAUSA: SEU BONECO FICA PARADO", cor = Cores.Muted, linhas = 1)
            }
            if (aba == "mapa") {
                val atual = mapa
                Row(
                    Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(12.u),
                    horizontalArrangement = Arrangement.spacedBy(12.u),
                ) {
                    Box(
                        Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .moldura(m, fundo = Color(0xFF08080E)),
                        contentAlignment = Alignment.Center,
                    ) {
                        when {
                            atual != null -> DesenhoDoMapa(atual, vaga, Modifier.fillMaxSize())
                            falhas >= 3 -> Texto("SEM MAPA AGORA (SÓ NAS FASES DA CAMPANHA E NA CASA)", cor = Cores.Muted)
                            else -> Texto("ABRINDO O MAPA...", cor = Cores.Muted)
                        }
                    }
                    if (atual != null) LegendaDoMapa(atual, vaga, Modifier.width(190.u).fillMaxHeight())
                }
            } else {
                ListaDoCaderno(caderno, cadernoFalhou, Modifier.weight(1f).fillMaxWidth()) { pedidoCaderno += 1 }
            }
        }
    }
}

/** O desenho: caixas (salas, corredores, cantos), marcas e um ponto por jogador (o seu pisca). */
@Composable
private fun DesenhoDoMapa(mapa: MapaJogo, vaga: Int, modifier: Modifier) {
    val m = LocalMedidas.current
    val medidor = rememberTextMeasurer()
    val claro = estilo(8, Cores.Bone)
    val escuro = estilo(8, Cores.Tinta)
    val pisca by piscando(350L)
    Canvas(modifier) {
        val borda = m.px(10)
        val esc = min((size.width - 2 * borda) / mapa.largura, (size.height - 2 * borda) / mapa.altura)
        val ox = (size.width - mapa.largura * esc) / 2f
        val oy = (size.height - mapa.altura * esc) / 2f
        fun ponto(x: Float, y: Float) = Offset(ox + x * esc, oy + y * esc)

        for (c in mapa.caixas) {
            val canto = ponto(c.x, c.y)
            val tam = Size(c.w * esc, c.h * esc)
            val fundo = c.fundo?.let { corHex(it) }
            if (fundo != null) drawRect(fundo, canto, tam)
            c.borda?.let { drawRect(corHex(it), canto, tam, style = Stroke(m.px(1))) }
            val texto = c.nome ?: c.sinal ?: continue
            val estiloTexto = if (fundo != null && fundo.luminance() > 0.35f) escuro else claro
            val medido = medidor.measure(texto, estiloTexto)
            if (medido.size.width <= tam.width - m.px(4) && medido.size.height <= tam.height) {
                drawText(
                    medido,
                    topLeft = Offset(
                        canto.x + (tam.width - medido.size.width) / 2f,
                        canto.y + (tam.height - medido.size.height) / 2f,
                    ),
                )
            }
            if (c.limpa) {
                // sala limpa: um visto verde no canto
                val v = m.px(3)
                val base = Offset(canto.x + tam.width - m.px(12), canto.y + m.px(8))
                drawLine(Cores.Moss, base, base + Offset(v, v), strokeWidth = m.px(2))
                drawLine(Cores.Moss, base + Offset(v, v), base + Offset(3 * v, -v), strokeWidth = m.px(2))
            }
        }
        for (mk in mapa.marcas) {
            val p = ponto(mk.x, mk.y)
            val cor = corHex(mk.cor)
            when (mk.tipo) {
                "door" -> {
                    drawRect(Color.Black, p - Offset(m.px(4), m.px(3)), Size(m.px(8), m.px(6)))
                    drawRect(cor, p - Offset(m.px(3), m.px(2)), Size(m.px(6), m.px(4)))
                }
                "portal" -> {
                    drawCircle(cor.copy(alpha = if (pisca) 1f else 0.5f), m.px(6), p, style = Stroke(m.px(2)))
                    drawCircle(cor, m.px(2), p)
                }
                else -> {
                    drawCircle(Color.Black, m.px(4), p)
                    drawCircle(cor, m.px(3), p)
                }
            }
        }
        // os jogadores por cima de tudo; o deste celular por último (e piscando)
        for (j in mapa.jogadores.sortedBy { it.vaga == vaga }) {
            val p = ponto(j.x, j.y)
            val cor = corHex(j.cor)
            val meu = j.vaga == vaga
            if (meu && pisca) drawCircle(Color.White, m.px(10), p, style = Stroke(m.px(2)))
            drawCircle(Color.White, m.px(6), p)
            drawCircle(if (j.caido) cor.copy(alpha = 0.4f) else cor, m.px(5), p)
            val nome = medidor.measure(if (meu) "VOCÊ" else j.nome, claro)
            val topo = Offset(p.x - nome.size.width / 2f, p.y - m.px(8) - nome.size.height)
            drawRect(Color.Black.copy(alpha = 0.7f), topo - Offset(m.px(2), 0f), Size(nome.size.width + m.px(4), nome.size.height.toFloat()))
            drawText(nome, topLeft = topo)
        }
    }
}

/** Do lado do mapa: o nome da fase e o que é cada cor. */
@Composable
private fun LegendaDoMapa(mapa: MapaJogo, vaga: Int, modifier: Modifier) {
    val m = LocalMedidas.current
    Column(
        modifier
            .moldura(m, fundo = Cores.Ink2)
            .verticalScroll(rememberScrollState())
            .padding(10.u),
        verticalArrangement = Arrangement.spacedBy(6.u),
    ) {
        Texto(mapa.titulo, cor = Cores.Brass, sombra = true)
        if (mapa.sub.isNotEmpty()) Texto(mapa.sub, cor = Cores.Muted)
        Spacer(Modifier.height(4.u))
        for (j in mapa.jogadores) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.u)) {
                Spacer(Modifier.size(8.u).drawBehind { drawCircle(corHex(j.cor)) })
                Texto(j.nome + if (j.vaga == vaga) " (VOCÊ)" else if (j.caido) " (CAÍDO)" else "", cor = Cores.Bone, linhas = 1)
            }
        }
        val vistas = mapa.marcas.filter { it.nome.isNotEmpty() }.distinctBy { it.nome }
        if (vistas.isNotEmpty()) Spacer(Modifier.height(4.u))
        for (mk in vistas) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.u)) {
                Spacer(
                    Modifier
                        .size(8.u)
                        .drawBehind { if (mk.tipo == "door") drawRect(corHex(mk.cor)) else drawCircle(corHex(mk.cor)) }
                )
                Texto(mk.nome, cor = Cores.Muted, linhas = 1)
            }
        }
        if (mapa.caixas.any { it.sinal == "?" }) {
            Spacer(Modifier.height(4.u))
            Texto("? = SALA QUE VOCÊS AINDA NÃO VIRAM", cor = Cores.Dim)
        }
    }
}

/** O CADERNO DE SEGREDOS, como no computador da Casa: o que já acharam e a dica do que falta. */
@Composable
private fun ListaDoCaderno(caderno: Caderno?, falhou: Boolean, modifier: Modifier, aoTentar: () -> Unit) {
    val m = LocalMedidas.current
    Column(
        modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.u, vertical = 12.u),
        verticalArrangement = Arrangement.spacedBy(10.u),
    ) {
        if (caderno == null) {
            if (falhou) {
                Texto("NÃO DEU PARA ABRIR O CADERNO.", cor = Cores.Muted)
                Botao("TENTAR DE NOVO", altura = 32) { aoTentar() }
            } else {
                Texto("ABRINDO O CADERNO...", cor = Cores.Muted)
            }
            return@Column
        }
        Texto("CADERNO DE SEGREDOS · ${caderno.achados} DE ${caderno.total}", tam = 16, cor = Cores.Brass, sombra = true)
        for (p in caderno.paginas) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .moldura(m, fundo = Cores.Ink3)
                    .padding(10.u),
                verticalArrangement = Arrangement.spacedBy(6.u),
            ) {
                val achados = p.segredos.count { it.achado }
                Texto("${p.lugar} · $achados DE ${p.segredos.size}", cor = Cores.Brass)
                for (sg in p.segredos) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.u)) {
                        Spacer(Modifier.size(6.u).drawBehind { drawRect(if (sg.achado) Cores.Moss else Cores.Dim) })
                        Texto(sg.texto, cor = if (sg.achado) Cores.Bone else Cores.Muted)
                    }
                }
            }
        }
    }
}
