package io.github.cauapbritto.soulstrike.controle.telas

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.graphics.TileMode
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.style.TextAlign
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.jogo.Me
import io.github.cauapbritto.soulstrike.controle.jogo.Melhoria
import io.github.cauapbritto.soulstrike.controle.jogo.Status
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Icone
import io.github.cauapbritto.soulstrike.controle.ui.ImagemPixel
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Segmentos
import io.github.cauapbritto.soulstrike.controle.ui.Tag
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.aoTocar
import io.github.cauapbritto.soulstrike.controle.ui.corVaga
import io.github.cauapbritto.soulstrike.controle.ui.imagemDoJogo
import io.github.cauapbritto.soulstrike.controle.ui.mistura
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.piscando
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** As telas de quando já está no jogo: o controle, a espera, a seleção, as melhorias, pênaltis e lojas. */
@Composable
fun TelaJogo() {
    val app = LocalApp.current
    val canal = app.canal
    val st = canal.status
    val me = st?.me
    if (st == null || me == null || !me.dono) {
        TelaEntrando(canal.vaga)
        return
    }
    val fase = st.fase
    val loja = me.loja
    val qual = when {
        fase == "playing" && me.jogando && loja != null && loja.tela -> "pc"
        fase == "playing" && me.jogando && loja != null -> "loja"
        fase == "penalty" && me.jogando && me.penalti != null -> "penalti"
        (fase == "playing" || fase == "paused") && me.jogando -> "controle"
        fase == "select" && me.jogando -> "selecao"
        fase == "choose" && me.jogando -> "melhorias"
        else -> "espera"
    }
    // trocou de tela: nada fica segurado da tela de antes
    LaunchedEffect(qual) { canal.entrada.soltarTudo() }
    when (qual) {
        "pc" -> TelaComputador(st, me, loja!!)
        "loja" -> TelaLoja(st, me, loja!!)
        "penalti" -> TelaPenaltis(me)
        "controle" -> TelaControle(st, me)
        "selecao" -> TelaSelecao(st, me)
        "melhorias" -> TelaMelhorias(me)
        else -> TelaEspera(st, me)
    }
}

/** Logo depois de escolher a vaga (ou voltando dela): o jogo ainda não respondeu. */
@Composable
private fun TelaEntrando(vaga: Int) {
    val pisca by piscando(400L)
    Column(
        Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.u, Alignment.CenterVertically),
    ) {
        if (vaga > 0) Tag(vaga, null, grande = true)
        Texto(if (pisca) "ENTRANDO NO JOGO..." else "ENTRANDO NO JOGO.. ", tam = 16, cor = Cores.Brass, sombra = true)
    }
}

// ── espera: menu, novidades, história, resultados ──

private fun textosDaEspera(st: Status, me: Me): Pair<String, String> {
    val fase = st.fase
    val banner = st.banner.uppercase()
    return when {
        fase == "news" -> (banner.ifEmpty { "NOVIDADES" }) to
            (if (st.paginaNovidade != null) "OS BOTÕES DAQUI TAMBÉM VIRAM AS NOTÍCIAS." else "NA TV: SETAS OU ENTER PARA ESCOLHER.")
        fase == "story" -> (banner.ifEmpty { "HISTÓRIA" }) to (if (me.jogando) "ACOMPANHE A HISTÓRIA NA TELA." else "")
        fase == "results" -> (banner.ifEmpty { "FIM DE JOGO" }) to
            (if (me.jogando) "ESCOLHA NO JOGO OU USE OS BOTÕES ABAIXO." else "")
        !me.jogando && (fase == "select" || fase == "playing" || fase == "paused" || fase == "penalty" || fase == "choose") ->
            "FORA DESTA PARTIDA" to "ESTE MODO NÃO USA O JOGADOR ${me.vaga}. AGUARDE A PRÓXIMA."
        fase == "lobby" -> "CONECTADO" to "TUDO CERTO! O ANFITRIÃO VAI AVANÇAR PARA A ESCOLHA DE PERSONAGENS."
        fase == "choose" -> "CONECTADO" to "OS JOGADORES ESTÃO ESCOLHENDO AS MELHORIAS."
        fase == "paused" -> "PAUSADO" to ""
        else -> "CONECTADO" to "AGUARDANDO O ANFITRIÃO ESCOLHER O MODO DE JOGO."
    }
}

@Composable
private fun TelaEspera(st: Status, me: Me) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    val (titulo, texto) = textosDaEspera(st, me)
    val fase = st.fase
    val pagina = if (fase == "news") st.paginaNovidade else null
    val lista = if (fase == "news") st.novidades else emptyList()
    var editarApelido by remember { mutableStateOf(false) }
    val resumo = if (fase == "results") st.resumo else null
    // rola quando não cabe, e fica no meio quando cabe (a altura mínima é a da tela)
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val alturaDaTela = maxHeight
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .heightIn(min = alturaDaTela)
                .padding(horizontal = 24.u, vertical = 16.u),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.u, Alignment.CenterVertically),
        ) {
            Tag(me.vaga, me.personagem, grande = true)
            Texto(titulo, tam = 16, cor = Cores.Brass, sombra = true, alinhar = TextAlign.Center)
            if (texto.isNotEmpty()) Texto(texto, Modifier.widthIn(max = 440.u), cor = Cores.Muted, alinhar = TextAlign.Center)
            if (resumo != null) CartaoResumo(resumo, me.vaga)
            if (pagina != null) {
                // a tela de novidades da TV (PLANTÃO): o número da notícia e o título
                Column(
                    Modifier
                        .widthIn(min = 240.u, max = 480.u)
                        .moldura(m, fundo = Cores.Ink2)
                        .drawBehind { drawRect(Color(0xFFD63434), size = Size(size.width, m.px(4))) }
                        .padding(start = 16.u, end = 16.u, top = 14.u, bottom = 10.u),
                    verticalArrangement = Arrangement.spacedBy(6.u),
                ) {
                    Texto(
                        if (pagina.indice > 0) "NOTÍCIA ${pagina.indice} DE ${pagina.total}" else "AS MANCHETES DE HOJE",
                        cor = Cores.Muted,
                    )
                    Texto(
                        if (pagina.indice > 0) pagina.titulo.uppercase() else "${pagina.total} NOVIDADES: APERTE > PARA COMEÇAR",
                        tam = 16, cor = Cores.Brass,
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.u)) {
                    Botao("<", Modifier.width(64.u), tam = 16, naHora = true) { canal.novidade("prev") }
                    Botao("PULAR", naHora = true) { canal.novidade("skip") }
                    Botao(">", Modifier.width(64.u), tipo = TipoBotao.PRINCIPAL, vaga = me.vaga, tam = 16, naHora = true) {
                        canal.novidade("next")
                    }
                }
            }
            if (lista.isNotEmpty()) {
                Column(Modifier.widthIn(max = 560.u), verticalArrangement = Arrangement.spacedBy(8.u)) {
                    for (linha in lista) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.u)) {
                            Spacer(
                                Modifier
                                    .padding(top = 3.u)
                                    .size(6.u)
                                    .drawBehind { drawRect(Cores.Moss) }
                            )
                            Texto(linha, cor = Cores.Bone)
                        }
                    }
                }
            }
            if (fase == "results" && me.jogando) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.u)) {
                    Botao("▲", Modifier.width(64.u), tam = 16, naHora = true) { canal.entrada.tocar("up") }
                    Botao("▼", Modifier.width(64.u), tam = 16, naHora = true) { canal.entrada.tocar("down") }
                    Botao("OK", Modifier.width(96.u), tipo = TipoBotao.PRINCIPAL, vaga = me.vaga, tam = 16, naHora = true) {
                        canal.entrada.tocar("confirm")
                    }
                }
            }
            if (fase == "story" && me.jogando) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.u)) {
                    Botao("AVANÇAR ▶", Modifier.widthIn(min = 160.u), tipo = TipoBotao.PRINCIPAL, vaga = me.vaga, tam = 16, naHora = true) {
                        canal.entrada.tocar("confirm")
                    }
                    Botao("PULAR", Modifier.widthIn(min = 120.u), naHora = true) { canal.entrada.tocar("pause") }
                }
            }
            if (st.temExtras && (fase == "lobby" || fase == "results")) BotoesDeReacao(altura = 36)
            if (st.temExtras && fase != "story") LinhaApelido(me.vaga) { editarApelido = true }
            FaixaAtualizar(canal.versaoJogo.ifEmpty { null })
            Botao("TROCAR DE JOGADOR", icone = R.drawable.i_trocar, altura = 32) { canal.trocarVaga() }
        }
        if (editarApelido) EditarApelido(aoFechar = { editarApelido = false })
    }
}

// ── seleção de personagem ─────────────────────

@Composable
private fun TelaSelecao(st: Status, me: Me) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    val heroi = canal.roster.getOrNull(me.personagem)
    val futebol = st.modo == "soccer"
    val basquete = futebol && st.hud == "basket"
    val pronto = me.pronto
    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Tag(me.vaga, me.personagem)
            Spacer(Modifier.weight(1f))
            if (st.temExtras) IconesDeReacao()
            Texto(nomeDoModo(st.modo, st.hud), cor = Cores.Muted, linhas = 1)
        }
        Row(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.u, vertical = 12.u),
            horizontalArrangement = Arrangement.spacedBy(24.u, Alignment.CenterHorizontally),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // ◀ herói ▶
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.u)) {
                Seta("◀", me.vaga, !pronto) { canal.entrada.tocar("char_left") }
                Pedestal(me.personagem, me.vaga, Modifier.size(150.u, 200.u))
                Seta("▶", me.vaga, !pronto) { canal.entrada.tocar("char_right") }
            }
            BoxWithConstraints(
                Modifier
                    .widthIn(max = 460.u)
                    .weight(1f, fill = false)
                    .fillMaxHeight()
            ) {
            val alto = maxHeight
            Column(
                Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .heightIn(min = alto),
                verticalArrangement = Arrangement.spacedBy(10.u, Alignment.CenterVertically),
            ) {
                if (heroi == null) {
                    Texto("CARREGANDO O ELENCO...", cor = Cores.Muted)
                } else {
                    Texto(heroi.nome.uppercase(), tam = 16, cor = Cores.Brass, sombra = true)
                    val linhas = if (futebol) listOf("VELOCIDADE" to heroi.velocidade / 5f)
                    else listOf(
                        "VIDA" to heroi.vida / 250f,
                        "VELOCIDADE" to heroi.velocidade / 5f,
                        "DANO" to (heroi.armas.maxOfOrNull { it.dano } ?: 0f) / 28f,
                    )
                    for ((nome, v) in linhas) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.u)) {
                            Texto(nome, Modifier.width(96.u), cor = Cores.Bone)
                            val segs = max(1, (min(1f, v) * 10f).roundToInt())
                            Segmentos(segs.toFloat(), null, 10f, Modifier.weight(1f))
                        }
                    }
                    // a habilidade (ou o SUPER do futebol e do basquete) e a arma de tiro
                    Column(verticalArrangement = Arrangement.spacedBy(4.u)) {
                        when {
                            basquete -> {
                                Texto("SUPER: " + heroi.superBasquete.uppercase(), cor = Cores.Brass)
                                if (heroi.superBasqueteDesc.isNotEmpty()) Texto(heroi.superBasqueteDesc, cor = Cores.Muted)
                                if (heroi.passivaBasquete.isNotEmpty()) {
                                    Texto("SEMPRE: " + heroi.passivaBasquete.uppercase(), cor = Cores.Brass)
                                }
                            }
                            futebol -> {
                                Texto("SUPER: " + heroi.superFutebol.uppercase(), cor = Cores.Brass)
                                if (heroi.superFutebolDesc.isNotEmpty()) Texto(heroi.superFutebolDesc, cor = Cores.Muted)
                                if (heroi.passivaFutebol.isNotEmpty()) {
                                    Texto("SEMPRE: " + heroi.passivaFutebol.uppercase(), cor = Cores.Brass)
                                    if (heroi.passivaFutebolDesc.isNotEmpty()) Texto(heroi.passivaFutebolDesc, cor = Cores.Muted)
                                }
                            }
                            else -> {
                                Texto(heroi.habilidade.uppercase(), cor = Cores.Brass)
                                if (heroi.habilidadeDesc.isNotEmpty()) Texto(heroi.habilidadeDesc, cor = Cores.Muted)
                                val tiro = heroi.armas.firstOrNull { !it.perto }
                                if (tiro != null && tiro.nota.isNotEmpty()) {
                                    Texto("${tiro.nome.uppercase()} (${tiro.pente} TIROS)", cor = Cores.Brass)
                                    Texto(tiro.nota, cor = Cores.Muted)
                                }
                            }
                        }
                    }
                    if (!futebol) {
                        val arma = heroi.armas.getOrNull(me.arma) ?: heroi.armas.firstOrNull()
                        if (arma != null) BotaoArma(arma.nome, arma.icone, arma.perto, ativo = !pronto) { canal.entrada.tocar("weapon") }
                    }
                }
                Botao(
                    if (pronto) "PRONTO! (TOQUE P/ CANCELAR)" else "PRONTO",
                    Modifier.fillMaxWidth(),
                    tipo = if (pronto) TipoBotao.VERDE else TipoBotao.PRINCIPAL,
                    vaga = me.vaga,
                    tam = 16,
                    altura = 48,
                    naHora = true,
                ) { canal.entrada.tocar(if (pronto) "cancel" else "confirm") }
            }
            }
        }
    }
}

/** As setas grandes da seleção (na cor da vaga). */
@Composable
private fun Seta(texto: String, vaga: Int, ativo: Boolean, aoTocar: () -> Unit) {
    val m = LocalMedidas.current
    val apertado = remember { mutableStateOf(false) }
    Box(
        Modifier
            .size(44.u, 56.u)
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .drawBehind {
                val e = m.px(2)
                drawRect(Cores.Edge, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(if (ativo) Cores.Ink4 else Cores.Desligado)
                drawRect(Color.White.copy(alpha = 0.18f), size = Size(size.width, e))
                drawRect(Color.White.copy(alpha = 0.18f), size = Size(e, size.height))
                val faixa = m.px(if (apertado.value) 2 else 6)
                drawRect(Color.Black.copy(alpha = 0.35f), Offset(0f, size.height - faixa), Size(size.width, faixa))
            }
            .aoTocar(ativo = ativo, naHora = true, apertado = apertado, acao = aoTocar),
        contentAlignment = Alignment.Center,
    ) {
        Texto(texto, tam = 16, cor = if (ativo) corVaga(vaga) else Cores.Dim, linha = 16)
    }
}

/** O herói em pé no pedestal (luz na cor da vaga e raios girando no fundo). */
@Composable
private fun Pedestal(personagem: Int, vaga: Int, modifier: Modifier = Modifier) {
    val m = LocalMedidas.current
    val img = imagemDoJogo(if (personagem >= 0) "/sprite/$personagem.png" else null)
    val cor = corVaga(vaga)
    Box(
        modifier
            .moldura(m, fundo = Cores.Ink2)
            .drawBehind {
                val c = Offset(size.width / 2f, size.height * 0.6f)
                // raios (o repeating-conic-gradient do site)
                for (i in 0 until 18) {
                    drawArc(
                        Color.White.copy(alpha = 0.035f), i * 20f - 90f, 10f, true,
                        topLeft = Offset(c.x - size.maxDimension, c.y - size.maxDimension),
                        size = Size(size.maxDimension * 2f, size.maxDimension * 2f),
                    )
                }
                drawRect(
                    Brush.radialGradient(
                        0f to cor.copy(alpha = 0.35f), 0.65f to Color.Transparent,
                        center = c, radius = size.maxDimension * 0.6f,
                    )
                )
            }
    ) {
        ImagemPixel(img, Modifier.fillMaxSize(), max = 3, pad = 16)
    }
}

/** ARMA: o desenho, o nome e se é de perto ou de tiro (toque troca na seleção). */
@Composable
fun BotaoArma(nome: String, icone: String, perto: Boolean, ativo: Boolean = true, aoTocar: () -> Unit) {
    val m = LocalMedidas.current
    val img = imagemDoJogo(icone.takeIf { it.isNotEmpty() }?.let { "/arma/$it" })
    val apertado = remember { mutableStateOf(false) }
    Row(
        Modifier
            .fillMaxWidth()
            .height(40.u)
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .drawBehind {
                val e = m.px(2)
                drawRect(Cores.Edge, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(if (ativo) Cores.Ink4 else Cores.Desligado)
                drawRect(Color.White.copy(alpha = 0.18f), size = Size(size.width, e))
                drawRect(Color.White.copy(alpha = 0.18f), size = Size(e, size.height))
                val faixa = m.px(if (apertado.value) 2 else 6)
                drawRect(Color.Black.copy(alpha = 0.35f), Offset(0f, size.height - faixa), Size(size.width, faixa))
            }
            .aoTocar(ativo = ativo, naHora = true, apertado = apertado, acao = aoTocar)
            .padding(start = 8.u, end = 12.u, bottom = 4.u),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.u, Alignment.CenterHorizontally),
    ) {
        if (img != null) ImagemPixel(img, Modifier.size(32.u, 32.u), max = 1, pad = 4)
        Texto(nome.uppercase() + if (perto) " · PERTO" else " · TIRO", cor = if (ativo) Cores.Bone else Cores.Dim, linhas = 1)
    }
}

// ── campanha: escolha de melhoria ─────────────

/** O desenho da melhoria pelo que ela faz (o upgradeIcon do site). */
private fun iconeDaMelhoria(o: Melhoria): Int {
    val t = (o.nome + " " + o.desc).uppercase()
    return when {
        Regex("VIDA|PELE|CURA|REGENER").containsMatchIn(t) -> R.drawable.i_coracao
        t.contains("ALMA") -> R.drawable.i_alma
        Regex("ENERGIA|RAIO").containsMatchIn(t) -> R.drawable.i_raio
        Regex("DANO|GOLPE|TIRO|ATIRA|PENTE|GATILHO").containsMatchIn(t) -> R.drawable.i_atacar
        Regex("ESQUIV|VELOC|RÁPID|CORR").containsMatchIn(t) -> R.drawable.i_esquiva
        else -> R.drawable.i_habilidade
    }
}

@Composable
private fun TelaMelhorias(me: Me) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    val pronto = me.pronto
    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Tag(me.vaga, me.personagem)
            Texto("ESCOLHA UMA MELHORIA", cor = Cores.Muted, linhas = 1)
        }
        Row(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(start = 16.u, end = 16.u, top = 16.u),
            horizontalArrangement = Arrangement.spacedBy(12.u),
        ) {
            for (i in 0 until 3) {
                val o = me.melhorias.getOrNull(i)
                if (o == null) {
                    Spacer(Modifier.weight(1f))
                    continue
                }
                val escolhida = i == me.escolha
                val cor = Color(o.cor)
                val apertado = remember { mutableStateOf(false) }
                Column(
                    Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .graphicsLayer {
                            translationY = if (apertado.value) m.px(2) else 0f
                            alpha = if (pronto) 0.55f else 1f
                        }
                        .drawBehind {
                            if (escolhida) {
                                val f = m.px(5)
                                drawRect(Cores.Brass, Offset(-f, -f), Size(size.width + 2 * f, size.height + 2 * f))
                                val g = m.px(3)
                                drawRect(Cores.Ink, Offset(-g, -g), Size(size.width + 2 * g, size.height + 2 * g))
                            }
                        }
                        .moldura(m, fundo = if (escolhida) Cores.Ink4 else Cores.Ink3)
                        .aoTocar(ativo = !pronto, naHora = true, apertado = apertado) { canal.entrada.tocar("opt${i + 1}") }
                        .padding(bottom = 10.u),
                    verticalArrangement = Arrangement.spacedBy(6.u),
                ) {
                    Box(
                        Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .padding(4.u)
                            .drawBehind {
                                drawRect(
                                    Brush.radialGradient(
                                        0f to mistura(cor, 0.4f, Color(0xFF1A1628)), 0.75f to Color(0xFF120F1E),
                                        center = Offset(size.width / 2f, size.height * 0.55f), radius = size.maxDimension * 0.75f,
                                    )
                                )
                                drawRect(Color.Black.copy(alpha = 0.55f), size = Size(size.width, m.px(2)))
                                drawRect(Color.Black.copy(alpha = 0.55f), size = Size(m.px(2), size.height))
                            },
                        contentAlignment = Alignment.Center,
                    ) {
                        Icone(iconeDaMelhoria(o), 64, sombra = true)
                    }
                    Texto(o.nome.uppercase(), Modifier.padding(horizontal = 10.u), tam = 16, cor = cor)
                    Texto(o.desc, Modifier.padding(horizontal = 10.u), cor = if (escolhida) Cores.Bone else Cores.Muted)
                }
            }
        }
        Botao(
            if (pronto) "PRONTO! (TOQUE P/ TROCAR)" else "CONFIRMAR",
            Modifier
                .fillMaxWidth()
                .padding(16.u),
            tipo = if (pronto) TipoBotao.VERDE else TipoBotao.PRINCIPAL,
            vaga = me.vaga,
            tam = 16,
            altura = 48,
            naHora = true,
        ) { canal.entrada.tocar(if (pronto) "cancel" else "confirm") }
    }
}

// ── pênaltis ──────────────────────────────────

/**
 * Pênaltis: tocar numa casa da grade deixa o analógico apontado para ela (o canto vale na hora do
 * chute para quem bate e na hora do PULAR para o goleiro). Só o celular mostra a grade.
 */
@Composable
private fun TelaPenaltis(me: Me) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    val pen = me.penalti ?: return
    val papel = pen.papel
    var casa by remember { mutableStateOf(0 to 1) }
    LaunchedEffect(papel) {
        canal.entrada.soltarTudo()
        casa = 0 to 1
    }
    fun escolher(col: Int, lin: Int) {
        casa = col to lin
        canal.entrada.eixo(col.toFloat(), (1 - lin).toFloat())
    }
    val titulo = when (papel) {
        "bate" -> "VOCÊ BATE"
        "defende" -> "VOCÊ DEFENDE"
        else -> "PÊNALTIS"
    }
    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Tag(me.vaga, me.personagem)
            Texto(
                if (pen.heroi.isNotEmpty()) "$titulo · ${pen.heroi.uppercase()}" else titulo,
                tam = 16, sombra = true, linhas = 1,
            )
        }
        Row(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.u, vertical = 12.u),
            horizontalArrangement = Arrangement.spacedBy(14.u),
        ) {
            // o gol: 3 x 3 casas (de cima para baixo), traves brancas e a rede
            Column(
                Modifier
                    .weight(1.5f)
                    .fillMaxHeight()
                    .graphicsLayer { alpha = if (papel == "espera") 0.35f else 1f }
                    .drawBehind {
                        drawRect(
                            Brush.linearGradient(
                                0f to Color(0xFF1B2A1E), 0.5f to Color(0xFF1B2A1E), 0.5f to Color(0xFF223526), 1f to Color(0xFF223526),
                                start = Offset.Zero, end = Offset(m.px(8.5f), m.px(8.5f)), tileMode = TileMode.Repeated,
                            )
                        )
                        val t = m.px(6)
                        drawRect(Cores.Bone, size = Size(size.width, t))
                        drawRect(Cores.Bone, size = Size(t, size.height))
                        drawRect(Cores.Bone, Offset(size.width - t, 0f), Size(t, size.height))
                    }
                    .padding(start = 14.u, end = 14.u, top = 14.u, bottom = 8.u),
                verticalArrangement = Arrangement.spacedBy(6.u),
            ) {
                for (lin in listOf(2, 1, 0)) {
                    Row(Modifier.weight(1f).fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.u)) {
                        for (col in listOf(-1, 0, 1)) {
                            val on = casa == col to lin
                            Box(
                                Modifier
                                    .weight(1f)
                                    .fillMaxHeight()
                                    .drawBehind {
                                        if (on) {
                                            val f = m.px(3)
                                            drawRect(Cores.Brass, Offset(-f, -f), Size(size.width + 2 * f, size.height + 2 * f))
                                            drawRect(Color(0xFF5A4520))
                                            drawRect(
                                                Brush.radialGradient(
                                                    0f to Color.Transparent, 1f to Cores.Brass.copy(alpha = 0.4f),
                                                    center = center, radius = size.maxDimension * 0.7f,
                                                )
                                            )
                                        } else {
                                            val u = m.px(1)
                                            drawRect(Cores.LineHi, Offset(-u, -u), Size(size.width + 2 * u, size.height + 2 * u))
                                            drawRect(Color(0xB3141022))
                                            drawRect(Color.Black.copy(alpha = 0.5f), size = Size(size.width, m.px(2)))
                                            drawRect(Color.Black.copy(alpha = 0.5f), size = Size(m.px(2), size.height))
                                        }
                                    }
                                    .aoTocar(ativo = papel != "espera", naHora = true) { escolher(col, lin) }
                            )
                        }
                    }
                }
            }
            Column(
                Modifier
                    .weight(1f)
                    .fillMaxHeight(),
                verticalArrangement = Arrangement.spacedBy(10.u, Alignment.CenterVertically),
            ) {
                when (papel) {
                    "bate" -> {
                        Texto("TOQUE NO CANTO · SÓ VOCÊ VÊ", cor = Cores.Muted)
                        Botao(
                            "CHUTE", Modifier.fillMaxWidth(), tipo = TipoBotao.DOURADO, tam = 16, sub = "SEGURE E SOLTE",
                            altura = 96, naHora = true, aoSoltar = { canal.entrada.soltar("attack") },
                        ) { canal.entrada.apertar("attack") }
                        Botao("CAVADINHA", Modifier.fillMaxWidth(), altura = 48, naHora = true) { canal.entrada.tocar("special") }
                    }
                    "defende" -> {
                        Texto("TOQUE NO LADO DO PULO", cor = Cores.Muted)
                        Botao("PULAR", Modifier.fillMaxWidth(), tipo = TipoBotao.DOURADO, tam = 16, altura = 96, naHora = true) {
                            canal.entrada.tocar("dodge")
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.u)) {
                            Botao(
                                "PROVOCAR", Modifier.weight(1f), altura = 48, naHora = true,
                                aoSoltar = { canal.entrada.soltar("attack") },
                            ) { canal.entrada.apertar("attack") }
                            Botao("CATIMBA", Modifier.weight(1f), altura = 48, naHora = true) { canal.entrada.tocar("mark") }
                        }
                    }
                    else -> Texto("AGORA NÃO É COM VOCÊ. OLHE A TV!", cor = Cores.Muted)
                }
            }
        }
    }
}
