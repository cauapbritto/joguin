package io.github.cauapbritto.soulstrike.controle.telas

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.input.InputTransformation
import androidx.compose.foundation.text.input.OutputTransformation
import androidx.compose.foundation.text.input.TextFieldLineLimits
import androidx.compose.foundation.text.input.TextFieldState
import androidx.compose.foundation.text.input.clearText
import androidx.compose.foundation.text.input.maxLengthTrim
import androidx.compose.foundation.text.input.rememberTextFieldState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.jogo.CartaArma
import io.github.cauapbritto.soulstrike.controle.jogo.Item
import io.github.cauapbritto.soulstrike.controle.jogo.Loja
import io.github.cauapbritto.soulstrike.controle.jogo.Me
import io.github.cauapbritto.soulstrike.controle.jogo.Status
import io.github.cauapbritto.soulstrike.controle.jogo.objetos
import io.github.cauapbritto.soulstrike.controle.jogo.texto
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Icone
import io.github.cauapbritto.soulstrike.controle.ui.ImagemPixel
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Niveis
import io.github.cauapbritto.soulstrike.controle.ui.Pilula
import io.github.cauapbritto.soulstrike.controle.ui.Segmentos
import io.github.cauapbritto.soulstrike.controle.ui.Tag
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.aoTocar
import io.github.cauapbritto.soulstrike.controle.ui.corHex
import io.github.cauapbritto.soulstrike.controle.ui.corVaga
import io.github.cauapbritto.soulstrike.controle.ui.desenharPixel
import io.github.cauapbritto.soulstrike.controle.ui.estilo
import io.github.cauapbritto.soulstrike.controle.ui.filtroCinza
import io.github.cauapbritto.soulstrike.controle.ui.imagemDoJogo
import io.github.cauapbritto.soulstrike.controle.ui.mistura
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.piscando
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlinx.coroutines.delay
import org.json.JSONObject
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

// ── as linhas da banca ────────────────────────
// As doações viram uma linha só (que abre a escolha de quem recebe) e os três encantos de uma
// arma viram uma linha só, com os encantos em botões no detalhe. Igual ao site.

private class Linha(
    val id: String,
    val rotulo: String,
    val custo: Int,
    val ok: Boolean,
    val podePagar: Boolean,
    val cor: String,
    val desc: String,
    val info: JSONObject?,
    val itens: List<Item>,
) {
    val tipo: String get() = info?.texto("type") ?: ""
}

/** O que vai ser comprado com a linha marcada (num grupo de encantos, o encanto escolhido). */
private class Oferta(val id: String, val custo: Int, val ok: Boolean, val podePagar: Boolean, val info: JSONObject?)

private fun linhaDoItem(id: String): String = when {
    id.startsWith("doar:") -> "doar"
    id.startsWith("encanto:") -> id.substring(0, id.lastIndexOf(':'))
    else -> id
}

private fun linhasDaLoja(loja: Loja): List<Linha> {
    val out = ArrayList<Linha>()
    val grupos = HashMap<String, MutableList<Item>>()
    for (it in loja.itens) {
        val row = linhaDoItem(it.id)
        if (row == "doar") {
            if (!grupos.containsKey("doar")) {
                val g = mutableListOf(it)
                grupos["doar"] = g
                out += Linha(
                    "doar", "DOAR ALMAS", it.custo, true, it.podePagar, "#c8aaff", "passa almas para um companheiro",
                    JSONObject().put("sub", "PARA UM AMIGO"), g,
                )
            }
        } else if (row != it.id) {
            val g = grupos[row]
            if (g == null) {
                val novo = mutableListOf(it)
                grupos[row] = novo
                val w = it.info?.optJSONObject("weapon")
                out += Linha(
                    row, w?.texto("name") ?: it.rotulo, it.custo, it.ok, it.podePagar, w?.texto("color") ?: it.cor,
                    it.desc, it.info, novo,
                )
            } else {
                g += it
            }
        } else {
            out += Linha(it.id, it.rotulo, it.custo, it.ok, it.podePagar, it.cor, it.desc, it.info, emptyList())
        }
    }
    return out
}

private fun itemDaLinha(r: Linha?, encantos: Map<String, String>): String? = when {
    r == null -> null
    r.id == "doar" -> r.itens.firstOrNull()?.id
    r.itens.isNotEmpty() -> encantos[r.id]?.takeIf { p -> r.itens.any { it.id == p } } ?: r.itens[0].id
    else -> r.id
}

private fun ofertaDaLinha(r: Linha?, encantos: Map<String, String>): Oferta? {
    if (r == null) return null
    if (r.itens.isEmpty() || r.id == "doar") return Oferta(r.id, r.custo, r.ok, r.podePagar, r.info)
    val id = itemDaLinha(r, encantos)
    val it = r.itens.firstOrNull { it.id == id } ?: r.itens[0]
    return Oferta(it.id, it.custo, it.ok, it.podePagar, it.info)
}

private fun JSONObject?.carta(nome: String): CartaArma? = this?.optJSONObject(nome)?.let { CartaArma(it) }

private fun JSONObject?.txt(nome: String): String = this?.texto(nome) ?: ""

/** Carimbo curto do que não dá para comprar. */
private fun carimbo(r: Linha): String {
    val sub = r.info.txt("sub").uppercase()
    return when {
        sub.contains("CHEIA") -> "CHEIA"
        sub.contains("VENDIDA") -> "VENDIDA"
        sub.contains("JÁ TEM") && !sub.contains("GRUPO") -> "JÁ É SUA"
        sub.isNotEmpty() && sub.length <= 10 -> sub
        else -> "NO MÁXIMO"
    }
}

private fun rotuloDaLinha(r: Linha): String {
    val info = r.info
    if (r.tipo == "forja" || r.tipo == "encanto") {
        val w = info.carta("weapon") ?: return r.rotulo
        return w.nome + (if (w.nivel > 0) " +${w.nivel}" else "") + (w.encanto?.let { " $it" } ?: "")
    }
    if (r.tipo == "fusao") return "FUNDIR AS 3"
    val heroi = info.txt("hero")
    if (heroi.isNotEmpty() && r.rotulo.startsWith("$heroi ")) return r.rotulo.substring(heroi.length + 1)
    return r.rotulo
}

/** Ícone de pixel dos itens que não são armas. */
private fun iconeDoItem(id: String, tipo: String): Int = when {
    tipo == "cupom" -> R.drawable.i_habilidade
    id == "pocao" -> R.drawable.i_pocao
    id == "energia" -> R.drawable.i_raio
    id == "arma" -> R.drawable.i_bau
    id == "trocar" -> R.drawable.i_trocar
    id == "continue" -> R.drawable.i_coracao
    id == "doar" -> R.drawable.i_alma
    else -> R.drawable.i_habilidade
}

private fun brilhoDoEncanto(chave: String?): Color? = when (chave) {
    "fogo" -> Color(0xFFFA8C3C)
    "gelo" -> Color(0xFF96D4F0)
    "raio" -> Color(0xFFF6D646)
    else -> null
}

/** A banca aberta: a marcação daqui, a do jogo (analógico na TV), a página dos CACOS e a doação. */
private class EstadoLoja {
    var escolha by mutableStateOf<String?>(null)
    var pagina by mutableStateOf("home")
    var doando by mutableStateOf(false)
    var doarPara by mutableStateOf<Int?>(null)
    var nota by mutableStateOf("")
    val encantos = mutableStateMapOf<String, String>()
    private var aberta = false
    private var servidor: String? = null

    private fun paginaDe(marcado: String?): String = when {
        marcado == null || marcado == "cupom" -> "home"
        marcado.startsWith("pet:") -> "pets"
        else -> "skins"
    }

    /** Acompanha o que o jogo marcou (alguém mexeu pelo analógico na TV). */
    fun sincronizar(loja: Loja, linhas: List<Linha>) {
        val marcado = loja.marcado
        if (!aberta) {
            aberta = true
            pagina = paginaDe(marcado)
            servidor = marcado
            val row = marcado?.let { linhaDoItem(it) }
            escolha = row
            if (row != null && marcado != row && row != "doar") encantos[row] = marcado
        } else if (marcado != servidor) {
            servidor = marcado
            if (loja.tipo == "cacos" && marcado != null && marcado != "cupom") pagina = paginaDe(marcado)
            val atual = linhas.firstOrNull { it.id == escolha }
            if (itemDaLinha(atual, encantos) != marcado && !doando) {
                val row = marcado?.let { linhaDoItem(it) }
                escolha = row
                if (row != null && marcado != row && row != "doar") encantos[row] = marcado
            }
        }
        if (linhas.none { it.id == escolha }) escolha = linhas.firstOrNull()?.id
    }
}

// ── a tela da banca ───────────────────────────

/** Loja, ferreiro, altar, loja de CACOS e armário, como no site (o ATACAR perto da banca abre). */
@Composable
fun TelaLoja(st: Status, me: Me, loja: Loja) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    val estado = remember(loja.tipo) { EstadoLoja() }
    val cupom = rememberTextFieldState()
    val linhas = remember(loja.o.toString()) { linhasDaLoja(loja) }
    estado.sincronizar(loja, linhas)
    val atual = linhas.firstOrNull { it.id == estado.escolha }
    val oferta = ofertaDaLinha(atual, estado.encantos)
    val cacos = loja.tipo == "cacos" || loja.tipo == "armario"
    val rapido = canal.rapido

    LaunchedEffect(estado.nota) {
        if (estado.nota.isNotEmpty()) {
            delay(3500)
            estado.nota = ""
        }
    }

    fun pedir(item: String, comprar: Boolean) = canal.pedirLoja(item, comprar)

    // voltar do Android: sai da doação ou fecha a banca (como o FECHAR)
    BackHandler {
        if (estado.doando) estado.doando = false else pedir("fechar", false)
    }

    fun enviarCupom() {
        val codigo = cupom.text.toString().trim().uppercase()
        if (codigo.isEmpty()) {
            estado.nota = "DIGITE O CUPOM"
            return
        }
        pedir("cupom:$codigo", true)
        cupom.clearText()
        estado.nota = "CUPOM ENVIADO"
        app.vibrador.tocar("compra")
    }

    fun comprar() {
        when (estado.escolha) {
            "cupom" -> enviarCupom()
            "doar" -> {
                estado.doarPara = null
                estado.doando = true
            }
            else -> {
                val id = itemDaLinha(atual, estado.encantos) ?: estado.escolha ?: return
                pedir(id, true)
                estado.nota = "PEDIDO ENVIADO"
                app.vibrador.tocar("compra")
            }
        }
    }

    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Tag(me.vaga, me.personagem)
            Texto(loja.titulo, Modifier.weight(1f), tam = 16, sombra = true, linhas = 1)
            if (rapido.energiaMax > 0 && loja.tipo != "altar") {
                Pilula(R.drawable.i_raio, "${rapido.energia}", Cores.Energy, unidade = "/${rapido.energiaMax}")
            }
            Pilula(if (cacos) R.drawable.i_caco else R.drawable.i_alma, "${loja.saldo}", if (cacos) Cores.Caco else Cores.Soul)
        }
        if (estado.doando) {
            Doacao(loja, estado, me.vaga) { para ->
                pedir("doar:$para", true)
                estado.doando = false
                estado.nota = "DOOU PARA P$para"
                app.vibrador.tocar("compra")
            }
            return@Column
        }
        BoxWithConstraints(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(start = 12.u, end = 12.u, top = 10.u, bottom = 10.u)
        ) {
            val estreita = maxWidth < m.dp(720)
            val larguraTela = maxWidth
            val digitando = tecladoAberto() && estado.escolha == "cupom"     // teclado aberto: só o cupom
            Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(12.u)) {
                val npc = loja.npc
                if (npc != null && !digitando) {
                    Vendedor(npc, Modifier.width(if (estreita) 72.u else 104.u).fillMaxHeight(), comFala = !estreita)
                }
                if (!digitando) Grade(
                    loja = loja,
                    linhas = linhas,
                    estado = estado,
                    larga = larguraTela >= m.dp(760),
                    modifier = Modifier.weight(1.25f).fillMaxHeight(),
                ) { r, item ->
                    estado.escolha = r
                    estado.nota = ""
                    if (item != null) pedir(item, false)
                }
                Column(
                    Modifier
                        .weight(1f)
                        .fillMaxHeight(),
                    verticalArrangement = Arrangement.spacedBy(10.u),
                ) {
                    Detalhe(
                        r = atual,
                        oferta = oferta,
                        loja = loja,
                        estado = estado,
                        cupom = cupom,
                        aoEnviarCupom = { enviarCupom() },
                        compacto = digitando,
                        modifier = Modifier.weight(1f).fillMaxWidth(),
                    ) { escolhido ->
                        val r = atual ?: return@Detalhe
                        estado.encantos[r.id] = escolhido
                        estado.nota = ""
                        pedir(escolhido, false)
                    }
                    val verbo = loja.acao ?: when {
                        loja.tipo == "altar" -> "ESCOLHER"
                        estado.escolha == "doar" -> "DOAR…"
                        oferta?.id == "fundir" -> "FUNDIR"
                        oferta?.info.txt("type") == "encanto" -> "ENCANTAR"
                        loja.tipo == "ferreiro" -> "FORJAR"
                        else -> "COMPRAR"
                    }
                    val preco = if (oferta != null && oferta.custo > 0 && loja.acao == null && estado.escolha != "doar") oferta.custo else 0
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.u)) {
                        Botao("FECHAR", Modifier.weight(1f), altura = 44, naHora = true) { pedir("fechar", false) }
                        BotaoComprar(
                            verbo, preco, cacos,
                            ativo = oferta != null && (oferta.ok || estado.escolha == "cupom") && oferta.podePagar,
                            modifier = Modifier.weight(1f),
                        ) { comprar() }
                    }
                    val nota = when {
                        estado.nota.isNotEmpty() -> estado.nota
                        oferta != null && !oferta.ok && estado.escolha != "cupom" -> oferta.info.txt("sub").ifEmpty { "INDISPONÍVEL" }
                        loja.acao != null -> ""
                        oferta != null && !oferta.podePagar -> "FALTAM ${oferta.custo - loja.saldo} ${loja.unidade}"
                        else -> ""
                    }
                    Texto(nota, Modifier.fillMaxWidth().heightIn(min = 12.u), cor = Cores.Muted, linhas = 1)
                }
            }
        }
    }
}

/** COMPRAR ◆ 40 (o preço vai dentro do botão). */
@Composable
private fun BotaoComprar(verbo: String, preco: Int, cacos: Boolean, ativo: Boolean, modifier: Modifier, aoTocar: () -> Unit) {
    val longo = verbo.length + (if (preco > 0) "$preco".length + 2 else 0) > 10
    Botao(
        if (preco > 0) "$verbo  $preco" else verbo,
        modifier,
        tipo = TipoBotao.VERDE,
        tam = if (longo) 8 else 16,
        icone = if (preco > 0) (if (cacos) R.drawable.i_caco else R.drawable.i_alma) else null,
        ativo = ativo,
        altura = 44,
        aoTocar = aoTocar,
    )
}

// ── quem atende ───────────────────────────────

/** O mascate, o ferreiro, o soldador...: 2 quadros alternando, o chão, o nome e a falinha. */
@Composable
private fun Vendedor(npc: Loja.Npc, modifier: Modifier, comFala: Boolean) {
    val m = LocalMedidas.current
    val a = imagemDoJogo("/npc/${npc.nome}_0.png")
    val b = imagemDoJogo("/npc/${npc.nome}_1.png")
    val outro by piscando(500L)
    BoxWithConstraints(modifier) {
        val alto = m.deTela(constraints.maxHeight.toFloat())
        Box(
            Modifier
                .fillMaxSize()
                .drawBehind {
                    val chao = m.px(18)
                    drawRect(
                        Brush.verticalGradient(listOf(Color(0xFF3A2A1C), Color(0xFF241A12)), startY = size.height - chao, endY = size.height),
                        Offset(0f, size.height - chao), Size(size.width, chao),
                    )
                    drawRect(Color(0xFF5A4430), Offset(0f, size.height - chao), Size(size.width, m.px(2)))
                    val img = (if (outro && b != null) b else a) ?: return@drawBehind
                    val esc = max(1f, min(2f, floor((alto - 60f) / img.height)))
                    val w = img.width * esc * m.k
                    val h = img.height * esc * m.k
                    val x = ((size.width - w) / 2f).roundToInt().toFloat()
                    val y = size.height - m.px(14) - h
                    desenharPixel(img, x, y, w, h)
                }
        ) {
            Texto(
                npc.rotulo, Modifier.align(Alignment.BottomCenter).padding(bottom = 3.u),
                cor = Cores.Brass, linhas = 1,
            )
            if (comFala && npc.fala.isNotEmpty()) {
                Box(
                    Modifier
                        .align(Alignment.TopCenter)
                        .fillMaxWidth()
                        .drawBehind {
                            val e = m.px(2)
                            drawRect(Color.Black.copy(alpha = 0.35f), Offset(m.px(3), m.px(3)), Size(size.width + e, size.height + e))
                            drawRect(Cores.Edge, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                            drawRect(Cores.Papel)
                            // o rabinho do balão
                            val p = m.px(4)
                            drawRect(Cores.Papel, Offset(m.px(14), size.height), Size(p * 2, p))
                            drawRect(Cores.Papel, Offset(m.px(14), size.height + p), Size(p, p))
                        }
                        .padding(start = 7.u, end = 7.u, top = 6.u, bottom = 5.u)
                ) {
                    Texto(npc.fala, cor = Cores.Tinta, linha = 10)
                }
            }
        }
    }
}

// ── a grade de cartões ────────────────────────

@Composable
private fun Grade(
    loja: Loja,
    linhas: List<Linha>,
    estado: EstadoLoja,
    larga: Boolean,
    modifier: Modifier,
    aoEscolher: (linha: String, item: String?) -> Unit,
) {
    val cacos = loja.tipo == "cacos"
    val mostradas = if (cacos) linhas.filter { it.id != "cupom" && it.info.txt("section") == estado.pagina } else linhas
    val topo = ArrayList<@Composable () -> Unit>()
    if (cacos) {
        val cup = linhas.firstOrNull { it.id == "cupom" }
        if (cup != null) {
            topo += {
                FaixaDaGrade("INSERIR CUPOM", estado.escolha == "cupom", fundo = Color(0xFFE9DFC0), cor = Cores.Tinta) {
                    aoEscolher("cupom", "cupom")
                }
            }
        }
        if (estado.pagina != "home") {
            topo += { FaixaDaGrade("< SEÇÕES", false) { estado.pagina = "home" } }
        }
    }
    val emCasa = cacos && estado.pagina == "home"
    val quantos = if (emCasa) 2 else mostradas.size
    val colunas = when {
        loja.tipo == "armario" -> if (larga) 5 else 4
        emCasa -> 2
        cacos -> 4
        quantos <= 4 -> 2
        quantos <= 9 -> 3
        else -> 4
    }
    val fileiras = ceil(quantos / colunas.toFloat()).toInt()
    val rolar = fileiras > (if (topo.isNotEmpty()) 2 else 3)
    Column(
        modifier.then(if (rolar) Modifier.verticalScroll(rememberScrollState()) else Modifier),
        verticalArrangement = Arrangement.spacedBy(8.u),
    ) {
        for (f in topo) f()
        if (emCasa) {
            Row(
                (if (rolar) Modifier.height(112.u) else Modifier.weight(1f)).fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.u),
            ) {
                SecaoDosCacos("skins", "SKINS", linhas, Color(0xFFB48CFF), Modifier.weight(1f)) { sec, primeira ->
                    estado.pagina = sec
                    if (primeira != null) aoEscolher(primeira, primeira)
                }
                SecaoDosCacos("pets", "PETS", linhas, Cores.Moss, Modifier.weight(1f)) { sec, primeira ->
                    estado.pagina = sec
                    if (primeira != null) aoEscolher(primeira, primeira)
                }
            }
        } else {
            for (i in 0 until fileiras) {
                Row(
                    (if (rolar) Modifier.height(112.u) else Modifier.weight(1f)).fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.u),
                ) {
                    for (j in 0 until colunas) {
                        val r = mostradas.getOrNull(i * colunas + j)
                        if (r == null) {
                            Spacer(Modifier.weight(1f))
                        } else {
                            CartaoDaLoja(r, loja, r.id == estado.escolha, Modifier.weight(1f).fillMaxHeight()) {
                                aoEscolher(r.id, itemDaLinha(r, estado.encantos))
                            }
                        }
                    }
                }
            }
        }
    }
}

/** As faixas baixas do topo da grade (INSERIR CUPOM e < SEÇÕES). */
@Composable
private fun FaixaDaGrade(
    texto: String,
    escolhida: Boolean,
    fundo: Color = Cores.Ink4,
    cor: Color = Cores.Bone,
    aoTocar: () -> Unit,
) {
    val m = LocalMedidas.current
    val apertado = remember { mutableStateOf(false) }
    Box(
        Modifier
            .fillMaxWidth()
            .height(32.u)
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .contornoDourado(m.px(1), escolhida)
            .moldura(m, fundo = fundo)
            .aoTocar(naHora = true, apertado = apertado, acao = aoTocar),
        contentAlignment = Alignment.Center,
    ) {
        Texto(texto, cor = cor, linhas = 1)
    }
}

/** Contorno dourado de quem está marcado (outline do site, 3 px para fora). */
private fun Modifier.contornoDourado(u: Float, on: Boolean): Modifier = if (!on) this else drawBehind {
    val f = 7f * u
    drawRect(Cores.Brass, Offset(-f, -f), Size(size.width + 2 * f, size.height + 2 * f))
    val g = 5f * u
    drawRect(Cores.Ink, Offset(-g, -g), Size(size.width + 2 * g, size.height + 2 * g))
}

/** Loja de CACOS, tela inicial: um cartão por seção (SKINS e PETS) com 3 desenhos. */
@Composable
private fun SecaoDosCacos(
    sec: String,
    nome: String,
    linhas: List<Linha>,
    cor: Color,
    modifier: Modifier,
    aoAbrir: (sec: String, primeira: String?) -> Unit,
) {
    val m = LocalMedidas.current
    val parte = linhas.filter { it.info.txt("section") == sec }
    val minhas = parte.count { val s = it.info.txt("state"); s == "tirar" || s == "vestir" }
    val sub = if (sec == "pets") "${parte.size} BICHINHOS · $minhas " + (if (minhas == 1) "SEU" else "SEUS")
    else "${parte.size} ROUPAS · $minhas " + (if (minhas == 1) "SUA" else "SUAS")
    val apertado = remember { mutableStateOf(false) }
    Column(
        modifier
            .fillMaxHeight()
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .moldura(m, fundo = Cores.Ink3)
            .aoTocar(naHora = true, apertado = apertado) { aoAbrir(sec, parte.firstOrNull()?.id) },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Row(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(start = 4.u, end = 4.u, top = 4.u)
                .drawBehind {
                    drawRect(
                        Brush.radialGradient(
                            0f to mistura(cor, 0.45f, Color(0xFF1A1628)), 0.75f to Color(0xFF120F1E),
                            center = Offset(size.width / 2f, size.height * 0.6f), radius = size.maxDimension * 0.75f,
                        )
                    )
                },
            horizontalArrangement = Arrangement.spacedBy(2.u, Alignment.CenterHorizontally),
            verticalAlignment = Alignment.Bottom,
        ) {
            parte.take(3).forEachIndexed { i, r ->
                val caminho = r.info.txt("img")
                val img = imagemDoJogo(caminho.ifEmpty { null })
                ImagemPixel(
                    img,
                    Modifier
                        .weight(1f)
                        .fillMaxHeight(if (i == 1) 0.95f else 0.8f),
                    max = 3, pad = 2, div = if (caminho.startsWith("/skin/")) 3 else 1,
                    embaixo = true, alpha = if (i == 1) 1f else 0.6f,
                )
            }
        }
        Texto(nome, tam = 16, cor = cor, linhas = 1)
        Texto(sub, Modifier.padding(bottom = 6.u), cor = Cores.Muted, linhas = 1)
    }
}

/** Um cartão da grade: o desenho no quadrinho, raridade, nível, carimbo, nome e preço. */
@Composable
private fun CartaoDaLoja(r: Linha, loja: Loja, escolhido: Boolean, modifier: Modifier, aoTocar: () -> Unit) {
    val m = LocalMedidas.current
    val app = LocalApp.current
    val info = r.info
    val fusao = r.tipo == "fusao"
    val w = info.carta("weapon") ?: if (fusao) info.carta("next") else null
    val desligado = !(r.ok && r.podePagar)
    val corNome = if (desligado) Cores.Dim else corHex(r.cor)
    val corFundo = corHex(w?.cor ?: r.cor, Cores.Comum)
    val estadoSkin = info.txt("state")
    val cacos = loja.tipo == "cacos" || loja.tipo == "armario"
    val apertado = remember { mutableStateOf(false) }
    val cinza = when {
        desligado -> filtroCinza(0.55f)
        loja.tipo == "armario" && (estadoSkin == "comprar" || estadoSkin == "cupom") -> filtroCinza(0.45f)
        else -> null
    }
    Column(
        modifier
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .contornoDourado(m.px(1), escolhido)
            .moldura(m, fundo = if (escolhido) Cores.Ink4 else Cores.Ink3)
            .aoTocar(naHora = true, apertado = apertado, acao = aoTocar),
    ) {
        Box(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(start = 4.u, end = 4.u, top = 4.u)
                .drawBehind {
                    drawRect(
                        Brush.radialGradient(
                            0f to mistura(corFundo, 0.45f, Color(0xFF1A1628)), 0.75f to Color(0xFF120F1E),
                            center = Offset(size.width / 2f, size.height * 0.55f), radius = size.maxDimension * 0.75f,
                        )
                    )
                    drawRect(Color.Black.copy(alpha = 0.55f), size = Size(size.width, m.px(2)))
                    drawRect(Color.Black.copy(alpha = 0.55f), size = Size(m.px(2), size.height))
                    drawRect(Color.White.copy(alpha = 0.06f), Offset(0f, size.height - m.px(2)), Size(size.width, m.px(2)))
                    drawRect(Color.White.copy(alpha = 0.06f), Offset(size.width - m.px(2), 0f), Size(m.px(2), size.height))
                    // sombrinha no chão do quadrinho
                    drawOval(
                        Brush.radialGradient(
                            0f to Color.Black.copy(alpha = 0.55f), 0.7f to Color.Transparent,
                            center = Offset(size.width / 2f, size.height * 0.94f - m.px(3)), radius = size.width * 0.3f,
                        ),
                        topLeft = Offset(size.width * 0.2f, size.height * 0.94f - m.px(6)), size = Size(size.width * 0.6f, m.px(6)),
                    )
                },
            contentAlignment = Alignment.Center,
        ) {
            val caminho = when {
                w != null -> w.icone.takeIf { it.isNotEmpty() }?.let { "/arma/$it" }
                else -> info.txt("img").ifEmpty { null }
            }
            if (caminho != null) {
                val img = imagemDoJogo(caminho)
                ImagemPixel(
                    img, Modifier.fillMaxSize(), max = 3, pad = 6,
                    div = if (caminho.startsWith("/skin/")) 3 else 1,
                    silhueta = fusao && !(info?.optBoolean("known") ?: false),
                    aura = if (fusao && !(info?.optBoolean("known") ?: false)) corFundo else null,
                    filtro = cinza,
                )
                if (fusao && !(info?.optBoolean("known") ?: false)) Texto("?", tam = 16, cor = Color.White, sombra = true)
            } else {
                Icone(iconeDoItem(r.id, r.tipo), 32, filtro = cinza, sombra = true)
            }
            // raridade (em cima à esquerda) e nível do ferreiro (em cima à direita)
            val rar = when {
                fusao -> "FORJADA"
                w != null -> w.raridade
                info.txt("tier") == "rara" -> "RARA"
                else -> ""
            }
            if (rar.isNotEmpty() && rar != "COMUM") {
                Box(
                    Modifier
                        .align(Alignment.TopStart)
                        .padding(2.u)
                        .drawBehind { drawRect(corFundo) }
                        .padding(start = 3.u, end = 3.u, top = 2.u)
                ) {
                    Texto(rar, cor = Color(0xFF0C0A14), linhas = 1, linha = 8)
                }
            }
            if ((r.tipo == "forja" || r.tipo == "encanto") && w != null) {
                Niveis(w.nivel, Modifier.align(Alignment.TopEnd).padding(top = 4.u, end = 4.u))
            }
            if (!r.ok && r.custo > 0 && estadoSkin.isEmpty()) {
                Box(
                    Modifier
                        .rotate(-12f)
                        .drawBehind {
                            val e = m.px(2)
                            drawRect(Cores.Blood, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                            drawRect(Color(0xCC0C0A14))
                        }
                        .padding(start = 4.u, end = 4.u, top = 3.u, bottom = 1.u)
                ) {
                    Texto(carimbo(r), cor = Cores.Blood, linhas = 1, linha = 8)
                }
            }
            if (info?.optBoolean("mine") == true) {
                Box(
                    Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth()
                        .drawBehind { drawRect(corVaga(app.canal.vaga)) }
                        .padding(top = 2.u),
                    contentAlignment = Alignment.Center,
                ) {
                    Texto("SEU HERÓI", cor = Color(0xFF0C0A14), linhas = 1, linha = 8)
                }
            }
        }
        Texto(
            rotuloDaLinha(r),
            Modifier
                .fillMaxWidth()
                .height(26.u)
                .padding(start = 6.u, end = 6.u, top = 4.u),
            cor = corNome, linhas = 2, linha = 10,
        )
        // o preço (ou a etiqueta do armário e da loja de CACOS)
        val corPreco = when {
            desligado -> Cores.Dim
            estadoSkin == "tirar" || estadoSkin == "vestir" -> Cores.Moss
            estadoSkin == "cupom" -> Cores.Brass
            cacos -> Cores.Caco
            else -> Cores.Soul
        }
        val (comGema, preco) = when {
            estadoSkin.isNotEmpty() -> (estadoSkin == "comprar") to info.txt("tag")
            r.custo > 0 -> true to "${r.custo}"
            else -> false to (if (loja.tipo == "altar") "ESCOLHER" else "GRÁTIS")
        }
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 2.u, end = 2.u, bottom = 4.u)
                .height(16.u)
                .drawBehind { drawRect(Cores.Bolso) },
            horizontalArrangement = Arrangement.spacedBy(3.u, Alignment.CenterHorizontally),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (comGema) Icone(if (cacos) R.drawable.i_caco else R.drawable.i_alma, 8)
            Texto(preco, cor = corPreco, linhas = 1, linha = 8)
        }
    }
}

// ── o detalhe ─────────────────────────────────

/** A luz no chão e os raios atrás do que está sendo mostrado. */
@Composable
private fun PedestalDaLoja(cor: Color, modifier: Modifier = Modifier, conteudo: @Composable RowScope.() -> Unit) {
    val m = LocalMedidas.current
    Row(
        modifier
            .fillMaxWidth()
            .drawBehind {
                val c = Offset(size.width / 2f, size.height * 0.6f)
                val r = size.maxDimension
                for (i in 0 until 18) {
                    drawArc(
                        Color.White.copy(alpha = 0.035f), i * 20f - 90f, 10f, true,
                        topLeft = Offset(c.x - r, c.y - r), size = Size(r * 2f, r * 2f),
                    )
                }
                drawRect(
                    Brush.radialGradient(
                        0f to cor.copy(alpha = 0.4f), 0.65f to Color.Transparent,
                        center = c, radius = size.maxDimension * 0.55f,
                    )
                )
                drawOval(
                    Brush.radialGradient(
                        0f to Color.Black.copy(alpha = 0.6f), 0.7f to Color.Transparent,
                        center = Offset(size.width / 2f, size.height - m.px(7)), radius = m.px(48),
                    ),
                    topLeft = Offset(size.width / 2f - m.px(48), size.height - m.px(12)), size = Size(m.px(96), m.px(10)),
                )
            },
        horizontalArrangement = Arrangement.spacedBy(8.u, Alignment.CenterHorizontally),
        verticalAlignment = Alignment.CenterVertically,
        content = conteudo,
    )
}

/** Uma arma num quadrinho: grande e brilhando (a que vai ganhar) ou pequena (a de agora). */
@Composable
private fun RowScope.DesenhoDaArma(
    w: CartaArma?,
    peso: Float = 1f,
    max: Int = 3,
    brilho: Color? = null,
    segredo: Boolean = false,
    alpha: Float = 1f,
    selo: String? = null,
) {
    val img = imagemDoJogo(w?.icone?.takeIf { it.isNotEmpty() }?.let { "/arma/$it" })
    val cor = corHex(w?.cor, Cores.Comum)
    Box(Modifier.weight(peso).fillMaxHeight(), contentAlignment = Alignment.Center) {
        ImagemPixel(
            img, Modifier.fillMaxSize(), max = max, pad = 6,
            aura = brilho ?: if (segredo) cor else null, silhueta = segredo, alpha = alpha,
        )
        if (segredo) Texto("?", tam = 16, cor = Color.White, sombra = true)
        if (selo != null) {
            Box(
                Modifier
                    .align(Alignment.TopEnd)
                    .drawBehind { drawRect(Cores.Brass) }
                    .padding(start = 3.u, end = 3.u, top = 2.u)
            ) {
                Texto(selo, cor = Color(0xFF0C0A14), linhas = 1, linha = 8)
            }
        }
    }
}

/** Quadrinho pequeno de arma (fusão e troca da mão). */
@Composable
private fun ArmaPequena(w: CartaArma?, borda: Color = Cores.Line, fundo: Color = Color(0xFF120F1E), alpha: Float = 1f) {
    val m = LocalMedidas.current
    val img = imagemDoJogo(w?.icone?.takeIf { it.isNotEmpty() }?.let { "/arma/$it" })
    Box(
        Modifier
            .size(40.u, 28.u)
            .drawBehind {
                val e = m.px(2)
                drawRect(borda, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(fundo)
            }
    ) {
        ImagemPixel(img, Modifier.fillMaxSize(), max = 1, pad = 4, alpha = alpha)
    }
}

/** Nome grande + etiqueta (raridade, PERTO/TIRO...). Nome comprido desce para 8 px. */
@Composable
private fun LinhaDoTitulo(nome: String, etiqueta: String?, cor: Color) {
    val m = LocalMedidas.current
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.u)) {
        Texto(nome, Modifier.weight(1f, fill = false), tam = if (nome.length > 17) 8 else 16, cor = cor, linhas = 1)
        if (!etiqueta.isNullOrEmpty()) {
            Box(
                Modifier
                    .drawBehind {
                        val e = m.px(2)
                        drawRect(cor)
                        drawRect(Cores.Ink2, Offset(e, e), Size(size.width - 2 * e, size.height - 2 * e))
                    }
                    .padding(start = 6.u, end = 6.u, top = 4.u, bottom = 2.u)
            ) {
                Texto(etiqueta, cor = cor, linhas = 1, linha = 8)
            }
        }
    }
}

/** Uma linha de comparação: nome, a barra em quadradinhos (o ganho piscando) e o número. */
@Composable
private fun LinhaDeNumero(nome: String, antes: Int, depois: Int? = null, max: Int = 60) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.u)) {
        Texto(nome, Modifier.width(64.u), cor = Cores.Muted, linhas = 1)
        Segmentos(antes.toFloat(), depois?.toFloat(), max.toFloat(), Modifier.weight(1f))
        Row {
            Texto("$antes", cor = Cores.Bone, linhas = 1)
            if (depois != null && depois != antes) Texto(" $depois", cor = Cores.Moss, linhas = 1)
        }
    }
}

@Composable
private fun LinhaDeTexto(nome: String, valor: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.u)) {
        Texto(nome, Modifier.width(64.u), cor = Cores.Muted, linhas = 1)
        Texto(valor, cor = Cores.Bone, linhas = 1)
    }
}

@Composable
private fun Detalhe(
    r: Linha?,
    oferta: Oferta?,
    loja: Loja,
    estado: EstadoLoja,
    cupom: TextFieldState,
    aoEnviarCupom: () -> Unit,
    compacto: Boolean,
    modifier: Modifier,
    aoEncanto: (String) -> Unit,
) {
    val m = LocalMedidas.current
    Column(
        modifier
            .moldura(m, fundo = Cores.Ink2)
            .padding(horizontal = 12.u, vertical = 10.u),
        verticalArrangement = Arrangement.spacedBy(6.u),
    ) {
        if (r == null) return@Column
        val info = r.info
        when (r.tipo) {
            "arma" -> DetalheArma(info)
            "forja", "encanto" -> DetalheForja(r, oferta, estado, aoEncanto)
            "fusao" -> DetalheFusao(info)
            "skin" -> {
                val caminho = info.txt("img")
                val img = imagemDoJogo(caminho.ifEmpty { null })
                val cor = corHex(r.cor)
                PedestalDaLoja(cor, Modifier.weight(1f).heightIn(min = 40.u)) {
                    ImagemPixel(
                        img, Modifier.weight(1f).fillMaxHeight(), max = 3, pad = 4,
                        div = if (caminho.startsWith("/skin/")) 3 else 1, aura = cor,
                    )
                }
                LinhaDoTitulo(r.rotulo, info.txt("rarity"), cor)
                Texto(info.txt("hero") + " · " + r.desc.uppercase(), cor = Cores.Muted)
                val sub = info.txt("sub")
                if (sub.isNotEmpty()) Texto(sub, cor = Cores.Muted)
            }
            "cupom" -> {
                val cor = corHex(r.cor, Color(0xFF78C8FF))
                Texto("INSERIR CUPOM", tam = 16, cor = cor)
                CampoDeTexto(
                    cupom, "DIGITE O CUPOM", cor,
                    fundo = Color(0xFFF0F0EC), corTexto = Color(0xFF1E1E28), maiusculas = true, maximo = 40,
                ) { aoEnviarCupom() }
                if (!compacto) Texto("CADA CUPOM VALE UMA VEZ E DÁ CACOS. ALGUNS DÃO UMA SKIN RARA JUNTO.", cor = Cores.Muted)
                val nota = info.txt("note")
                if (nota.isNotEmpty()) Texto(nota, cor = cor)
            }
            "tela" -> {
                val linhas = info?.optJSONArray("lines")
                Column(
                    Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .moldura(m, fundo = Color(0xFF0C1224), luz = Color(0xFF3A4A70), sombra = Color(0xFF3A4A70), fora = 0)
                        .padding(horizontal = 8.u, vertical = 6.u),
                    verticalArrangement = Arrangement.Bottom,
                ) {
                    if (linhas != null) for (i in 0 until linhas.length()) {
                        Texto(linhas.optString(i).ifEmpty { " " }, cor = Color(0xFFCFE0FF), linhas = 1)
                    }
                }
            }
            else -> {
                val cor = corHex(r.cor)
                PedestalDaLoja(cor, Modifier.weight(1f).heightIn(min = 40.u, max = 120.u)) {
                    Icone(iconeDoItem(r.id, r.tipo), 48, sombra = true)
                }
                LinhaDoTitulo(r.rotulo, info.txt("sub"), cor)
                Texto(r.desc.uppercase(), cor = Cores.Muted)
            }
        }
    }
}

@Composable
private fun ColumnScope.DetalheArma(info: JSONObject?) {
    val w = info.carta("weapon") ?: return
    val cor = corHex(w.cor, Cores.Comum)
    PedestalDaLoja(cor, Modifier.weight(1f).heightIn(min = 40.u, max = 120.u)) {
        DesenhoDaArma(w, brilho = cor)
    }
    LinhaDoTitulo(w.nome, w.raridade + " · " + if (w.perto) "PERTO" else "TIRO", cor)
    val dono = info.txt("owner")
    if (dono.isNotEmpty()) Texto("DO $dono", cor = Cores.Muted)
    LinhaDeNumero("DANO", w.dano)
    if (w.pente > 0) LinhaDeNumero("PENTE", w.pente, max = 30)
    w.textoEnergia?.let { LinhaDeTexto("ENERGIA", it) }
    val sai = info.carta("out")
    if (sai != null) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.u)) {
            Texto("TROCA", cor = Cores.Muted, linhas = 1)
            ArmaPequena(sai, borda = Cores.Blood, fundo = Color(0xFF2A1420), alpha = 0.5f)
            Texto(">", tam = 16, cor = Cores.Brass)
            ArmaPequena(w, borda = Cores.Moss, fundo = Color(0xFF14301E))
            Texto("SAI: ${sai.nome}", cor = Cores.Muted, linhas = 1)
        }
    }
}

@Composable
private fun ColumnScope.DetalheForja(r: Linha, oferta: Oferta?, estado: EstadoLoja, aoEncanto: (String) -> Unit) {
    val encanto = r.tipo == "encanto"
    val it = if (encanto) (oferta?.info ?: r.info) else r.info
    val agora = it.carta("weapon") ?: return
    val prox = it.carta("next")
    val cor = corHex(agora.cor, Cores.Comum)
    val chave = it?.optJSONObject("enchant")?.texto("key")
    PedestalDaLoja(cor, Modifier.weight(1f).heightIn(min = 40.u, max = 120.u)) {
        DesenhoDaArma(agora, peso = 0.6f, max = 2, alpha = 0.75f)
        if (prox != null) {
            Texto(">", tam = 16, cor = Cores.Brass)
            DesenhoDaArma(
                prox, brilho = if (prox.encanto != null) brilhoDoEncanto(chave) ?: corHex(prox.cor) else corHex(prox.cor),
                selo = "+${prox.nivel}",
            )
        }
    }
    val rotulo = agora.nome + if (agora.nivel > 0) " +${agora.nivel}" else ""
    LinhaDoTitulo(
        if (prox != null) "$rotulo > +${prox.nivel}" + (prox.encanto?.let { e -> " $e" } ?: "") else "$rotulo · NO MÁXIMO",
        agora.raridade, cor,
    )
    if (encanto) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.u)) {
            for (opcao in r.itens) {
                val en = opcao.info?.optJSONObject("enchant") ?: continue
                ChipDeEncanto(
                    en.texto("name"), en.texto("desc"), corHex(en.texto("color")),
                    on = opcao.id == oferta?.id, modifier = Modifier.weight(1f),
                ) { aoEncanto(opcao.id) }
            }
        }
    }
    LinhaDeNumero("DANO", agora.dano, prox?.dano)
    if (agora.pente > 0) LinhaDeNumero("PENTE", agora.pente, prox?.pente, max = 30)
    agora.textoEnergia?.let { t -> LinhaDeTexto("ENERGIA", t) }
}

@Composable
private fun ChipDeEncanto(nome: String, desc: String, cor: Color, on: Boolean, modifier: Modifier, aoTocar: () -> Unit) {
    val m = LocalMedidas.current
    val apertado = remember { mutableStateOf(false) }
    Column(
        modifier
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .contornoDourado(m.px(1) * 0.75f, on)
            .drawBehind {
                val e = m.px(2)
                drawRect(Cores.Edge, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(mistura(cor, if (on) 0.3f else 0.12f, Cores.Ink))
                drawRect(Color.White.copy(alpha = 0.1f), size = Size(size.width, e))
                drawRect(Color.White.copy(alpha = 0.1f), size = Size(e, size.height))
            }
            .aoTocar(naHora = true, apertado = apertado, acao = aoTocar)
            .padding(start = 2.u, end = 2.u, top = 6.u, bottom = 4.u),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.u),
    ) {
        Texto(nome, cor = cor, linhas = 1, alinhar = TextAlign.Center)
        Texto(desc, cor = Cores.Muted, linhas = 1, alinhar = TextAlign.Center)
    }
}

@Composable
private fun ColumnScope.DetalheFusao(info: JSONObject?) {
    val sai = info.carta("next") ?: return
    val conhecida = info?.optBoolean("known") ?: false
    val cor = corHex(sai.cor, Cores.Comum)
    val entradas = info?.optJSONArray("inputs").objetos().map { CartaArma(it) }
    PedestalDaLoja(cor, Modifier.weight(1f).heightIn(min = 40.u, max = 120.u)) {
        Row(horizontalArrangement = Arrangement.spacedBy(6.u)) {
            for (c in entradas) ArmaPequena(c)
        }
        Texto(">", tam = 16, cor = Cores.Brass)
        DesenhoDaArma(
            sai, max = 2, brilho = if (conhecida) cor else null, segredo = !conhecida,
            selo = if (conhecida && sai.nivel > 0) "+${sai.nivel}" else null,
        )
    }
    val familia = info.txt("family")
    val nome = if (conhecida) sai.nome + (if (sai.nivel > 0) " +${sai.nivel}" else "")
    else "???" + if (familia.isNotEmpty()) " TIPO $familia" else ""
    LinhaDoTitulo(nome, "FORJADA", cor)
    val nota = info.txt("note")
    if (nota.isNotEmpty()) Texto(nota, cor = Cores.Muted)
    if (conhecida) {
        LinhaDeNumero("DANO", sai.dano)
        sai.textoEnergia?.let { LinhaDeTexto("ENERGIA", it) }
    }
    Texto("AS 3 SOMEM E AS SUAS VOLTAM AO +0.", cor = Cores.Muted)
}

/** Senha: só asteriscos na tela (a fonte do jogo não tem bolinha). */
private val OCULTAR = OutputTransformation { if (length > 0) replace(0, length, "*".repeat(length)) }

/** Caixa de digitar (cupom e computador) na fonte do jogo. */
@Composable
fun CampoDeTexto(
    estado: TextFieldState,
    dica: String,
    borda: Color,
    fundo: Color,
    corTexto: Color,
    maiusculas: Boolean,
    maximo: Int,
    modifier: Modifier = Modifier,
    senha: Boolean = false,
    aoEnviar: () -> Unit,
) {
    val m = LocalMedidas.current
    BasicTextField(
        state = estado,
        modifier = modifier
            .fillMaxWidth()
            .drawBehind {
                val e = m.px(2)
                drawRect(borda, Offset(-e, -e), Size(size.width + 2 * e, size.height + 2 * e))
                drawRect(fundo)
            }
            .padding(horizontal = 8.u, vertical = 8.u),
        inputTransformation = InputTransformation.maxLengthTrim(maximo),
        outputTransformation = if (senha) OCULTAR else null,
        textStyle = estilo(16, corTexto),
        keyboardOptions = KeyboardOptions(
            capitalization = if (maiusculas) KeyboardCapitalization.Characters else KeyboardCapitalization.None,
            autoCorrectEnabled = false,
            keyboardType = if (senha) KeyboardType.Password else KeyboardType.Ascii,
            imeAction = ImeAction.Send,
        ),
        onKeyboardAction = { aoEnviar() },
        lineLimits = TextFieldLineLimits.SingleLine,
        cursorBrush = SolidColor(corTexto),
        decorator = { campo ->
            Box {
                if (estado.text.isEmpty()) Texto(dica, tam = 16, cor = corTexto.copy(alpha = 0.4f), linhas = 1)
                campo()
            }
        },
    )
}

// ── doar: escolher quem recebe ────────────────

@Composable
private fun Doacao(loja: Loja, estado: EstadoLoja, vaga: Int, aoDoar: (Int) -> Unit) {
    val m = LocalMedidas.current
    val doacao = loja.itens.firstOrNull { linhaDoItem(it.id) == "doar" }
    val para = estado.doarPara
    Column(
        Modifier
            .fillMaxSize()
            .padding(start = 12.u, end = 12.u, top = 10.u, bottom = 10.u),
        verticalArrangement = Arrangement.spacedBy(12.u),
    ) {
        Texto("PARA QUEM?", cor = Cores.Muted)
        Row(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(4.u),
            horizontalArrangement = Arrangement.spacedBy(12.u),
        ) {
            for (c in loja.colegas) {
                val cor = corVaga(c.vaga)
                val on = c.vaga == para
                val apertado = remember { mutableStateOf(false) }
                Column(
                    Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
                        .contornoDourado(m.px(1) * 1.6f, on)
                        .drawBehind {
                            val f = m.px(4)
                            drawRect(cor, Offset(-f, -f), Size(size.width + 2 * f, size.height + 2 * f))
                        }
                        .moldura(m, fundo = if (on) Cores.Ink4 else Cores.Ink3)
                        .aoTocar(naHora = true, apertado = apertado) { estado.doarPara = c.vaga }
                        .padding(12.u),
                    verticalArrangement = Arrangement.spacedBy(8.u),
                ) {
                    Texto("${c.rotulo} · ${c.nome}", tam = 16, cor = cor, linhas = 2)
                    Texto("${c.almas} ALMAS", cor = Cores.Muted)
                    if (on) Texto("FICA COM ${c.almas + (doacao?.custo ?: 0)}", cor = Cores.Bone)
                }
            }
            if (loja.colegas.isEmpty()) Texto("NINGUÉM PARA RECEBER AGORA.", cor = Cores.Muted)
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.u)) {
            Botao("VOLTAR", Modifier.weight(1f), altura = 44, naHora = true) { estado.doando = false }
            Botao(
                if (para == null) "DOAR" else "DOAR PARA P$para",
                Modifier.weight(1f),
                tipo = TipoBotao.VERDE,
                tam = 16,
                altura = 44,
                ativo = para != null && doacao != null && doacao.podePagar,
                vaga = vaga,
            ) { if (para != null) aoDoar(para) }
        }
    }
}
