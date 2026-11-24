package io.github.cauapbritto.soulstrike.controle.telas

import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.geometry.isSpecified
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.PathOperation
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.PointerId
import androidx.compose.ui.input.pointer.changedToDownIgnoreConsumed
import androidx.compose.ui.input.pointer.changedToUpIgnoreConsumed
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChangedIgnoreConsumed
import androidx.compose.ui.layout.layout
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.res.imageResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.IntOffset
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.jogo.BotaoHud
import io.github.cauapbritto.soulstrike.controle.jogo.DefBotao
import io.github.cauapbritto.soulstrike.controle.jogo.Entrada
import io.github.cauapbritto.soulstrike.controle.jogo.EstiloBotao
import io.github.cauapbritto.soulstrike.controle.jogo.Heroi
import io.github.cauapbritto.soulstrike.controle.jogo.Hud
import io.github.cauapbritto.soulstrike.controle.jogo.Inclinacao
import io.github.cauapbritto.soulstrike.controle.jogo.Mao
import io.github.cauapbritto.soulstrike.controle.jogo.Me
import io.github.cauapbritto.soulstrike.controle.jogo.PosBotao
import io.github.cauapbritto.soulstrike.controle.jogo.Rapido
import io.github.cauapbritto.soulstrike.controle.jogo.Status
import io.github.cauapbritto.soulstrike.controle.jogo.nomeCurto
import io.github.cauapbritto.soulstrike.controle.jogo.nomeDoPerfil
import io.github.cauapbritto.soulstrike.controle.jogo.perfilDoModo
import io.github.cauapbritto.soulstrike.controle.jogo.posicoesDosBotoes
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Pilula
import io.github.cauapbritto.soulstrike.controle.ui.Tag
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.aoTocar
import io.github.cauapbritto.soulstrike.controle.ui.corVaga
import io.github.cauapbritto.soulstrike.controle.ui.corVagaEscura
import io.github.cauapbritto.soulstrike.controle.ui.desenharPixel
import io.github.cauapbritto.soulstrike.controle.ui.filtroCinza
import io.github.cauapbritto.soulstrike.controle.ui.imagemDoJogo
import io.github.cauapbritto.soulstrike.controle.ui.mistura
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.u
import android.view.Surface
import kotlinx.coroutines.launch
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** Pixels (do jogo) fora do botão que ainda contam como toque nele. */
private const val IMA = 26f

/** Deslizando o dedo: até onde ele pode sair do botão sem soltar. */
private const val SEGURA = 40f

/** Margem em volta de cada botão: anel de recarga, sombra e a plaquinha do nome. */
private const val MARGEM = 14

// ── os botões de cada modo ────────────────────

/** Os botões do arco de cada modo (o mesmo do site, com o basquete sem o COLADO que ele não usa). */
fun botoesDoModo(perfil: String, heroi: Heroi?, mao: Mao?): List<DefBotao> {
    fun curto(s: String?, padrao: String): String = s?.trim()?.uppercase()?.takeIf { it.isNotEmpty() }?.let { nomeCurto(it) } ?: padrao
    return when (perfil) {
        "futebol" -> listOf(
            DefBotao("attack", "main", "CHUTAR", R.drawable.i_bola, EstiloBotao.PRINCIPAL),
            DefBotao("special", "w", "PASSE", R.drawable.i_passe),
            DefBotao("mark", "nw", "MARCAR", R.drawable.i_marcar, EstiloBotao.MARCAR),
            DefBotao("dodge", "n", "CORTE", R.drawable.i_corte),
            DefBotao("dribble", "ww", "COLADO", R.drawable.i_colado),
            DefBotao("super", "nn", curto(heroi?.superFutebol, "SUPER"), R.drawable.i_habilidade, EstiloBotao.SUPER),
        )
        "basquete" -> listOf(
            DefBotao("attack", "main", "ARREMESSO", R.drawable.i_bola, EstiloBotao.PRINCIPAL),
            DefBotao("special", "w", "PASSE", R.drawable.i_passe),
            DefBotao("mark", "nw", "MARCAR", R.drawable.i_marcar, EstiloBotao.MARCAR),
            DefBotao("dodge", "n", "CORTE", R.drawable.i_corte),
            DefBotao("super", "nn", curto(heroi?.superBasquete, "SUPER"), R.drawable.i_habilidade, EstiloBotao.SUPER),
        )
        "luta" -> listOf(
            DefBotao("attack", "main", "SOCO", R.drawable.i_atacar, EstiloBotao.PRINCIPAL),
            DefBotao("special", "w", "CHUTE", R.drawable.i_corte),
            DefBotao("sprint", "nw", "FORTE", R.drawable.i_raio),
            DefBotao("dodge", "n", "PULO", R.drawable.i_esquiva),
            DefBotao("dribble", "ww", "ESPECIAL", R.drawable.i_habilidade, EstiloBotao.SUPER),
            DefBotao("super", "nn", "SUPER", R.drawable.i_raio, EstiloBotao.SUPER),
        )
        else -> listOfNotNull(
            DefBotao(
                "attack", "main", curto(mao?.nome, "ATACAR"), R.drawable.i_atacar, EstiloBotao.PRINCIPAL,
                desenhoDoJogo = mao?.icone?.takeIf { it.isNotEmpty() }?.let { "/arma/$it" },
            ),
            DefBotao("special", "w", curto(heroi?.habilidade, "HABILIDADE"), R.drawable.i_habilidade, EstiloBotao.HABILIDADE),
            DefBotao("switch", "nw", "TROCAR ARMA", R.drawable.i_trocar),
            DefBotao("dodge", "n", "ESQUIVA", R.drawable.i_esquiva),
            if (perfil == "campanha") DefBotao("drop", "nn", "LARGAR", R.drawable.i_largar) else null,
        )
    }
}

/** O anel em volta de um botão: recarga do SUPER, munição ou energia. */
private class Anel(val p: Float, val cor: Color, val apagado: Boolean = false, val pronto: Boolean = false)

/** O contador em cima do ATACAR (munição ou energia). */
private class Contador(val texto: String, val recarga: Boolean, val vazio: Boolean)

private fun aneisDoModo(perfil: String, r: Rapido): Map<String, Anel> {
    val out = HashMap<String, Anel>()
    when (perfil) {
        "futebol", "basquete" -> {
            val cd = r.cooldown
            out["super"] = Anel((1f - cd).coerceIn(0f, 1f), Cores.Brass, apagado = cd > 0f, pronto = cd <= 0f)
        }
        "luta" -> {
            val en = r.energia.toFloat()
            val custo = (if (r.custo > 0) r.custo else 10).toFloat()
            val max = (if (r.energiaMax > 0) r.energiaMax else 30).toFloat()
            out["dribble"] = Anel(min(1f, en / custo), Cores.Brass, apagado = en < custo, pronto = en >= custo)
            out["super"] = Anel(min(1f, en / max), Cores.Brass, apagado = en < max, pronto = en >= max)
        }
        else -> {
            if (perfil == "campanha" && r.energiaMax > 0 && r.pente <= 0 && r.custo > 0) {
                out["attack"] = Anel(min(1f, r.energia.toFloat() / r.energiaMax), Cores.Energy)
            } else if (r.pente > 0) {
                val recarga = r.recarga > 0f
                val extra = !recarga && r.municao > r.pente
                val p = if (recarga) r.recarga else min(1f, r.municao.toFloat() / r.pente)
                out["attack"] = Anel(p.coerceIn(0f, 1f), if (recarga || extra) Cores.Brass else Cores.Moss)
            }
        }
    }
    return out
}

private fun contadorDoModo(perfil: String, r: Rapido): Contador? {
    if (perfil != "duelo" && perfil != "campanha") return null
    if (perfil == "campanha" && r.energiaMax > 0 && r.pente <= 0 && r.custo > 0) {
        val sem = r.energia < r.custo
        return Contador(if (sem) "SEM ENERGIA" else "ENERGIA ${r.energia}", recarga = false, vazio = sem)
    }
    if (r.pente <= 0) return null
    val recarga = r.recarga > 0f
    val vazio = !recarga && r.municao <= 0
    val texto = when {
        recarga -> "RECARGA"
        vazio -> "VAZIO"
        else -> "${r.municao}/${r.pente}"
    }
    return Contador(texto, recarga, vazio)
}

private fun dicaDoModo(perfil: String): String = when (perfil) {
    "futebol", "basquete" -> "empurre até a borda para correr"
    "luta" -> "para trás defende, para baixo agacha"
    else -> "mova o analógico"
}

// ── o toque: analógico e botões (vários dedos ao mesmo tempo) ──

/** Onde o analógico fica (o placeStick do site): sem sair da zona nem subir na barra de cima. */
private fun encaixar(za: Rect, s: Float, k: Float, p: Offset): Offset {
    val esquerda = max(8f * k, min(p.x - za.left - s / 2f, za.width - s - 8f * k))
    val topo = max(56f * k, min(p.y - za.top - s / 2f, za.height - s - 8f * k))
    return Offset(za.left + esquerda + s / 2f, za.top + topo + s / 2f)
}

private fun Hud.comBotao(acao: String, f: (BotaoHud) -> BotaoHud): Hud =
    copy(botoes = botoes + (acao to f(botoes[acao] ?: BotaoHud())))

private fun arredondar(v: Float): Float = (v * 10f).roundToInt() / 10f

/**
 * Os dedos no controle. O analógico aparece onde o polegar encosta (ou fica parado, se FIXO);
 * o botão que vale é o mais perto do dedo (não precisa acertar em cheio) e dá para deslizar de
 * um para outro. Nos AJUSTES DO CONTROLE, os mesmos toques arrastam os botões e o analógico.
 */
private class Pad(private val entrada: Entrada) {
    // geometria (a tela atualiza a cada mudança)
    var botoes: List<PosBotao> = emptyList()
    var zonaBotoes = Rect.Zero
    var zonaAnalogico = Rect.Zero
    var k = 2f
    var tamBase = 280f
    var centroPadrao = Offset.Zero
    var futebol = false
    var fixo = false
    var editando = false
    /** INCLINAR: o sensor move o analógico e tocar na zona dele zera. */
    var inclinando = false
    var aoZerar: () -> Unit = {}
    var hud = Hud()
    var chave: Any? = null
    var toque: () -> Unit = {}
    var aoCorrer: () -> Unit = {}
    var mudarHud: (Hud) -> Unit = {}

    // o que aparece na tela
    var centro by mutableStateOf(Offset.Unspecified)
    var pino by mutableStateOf(Offset.Zero)
    var vivo by mutableStateOf(false)
    var correndo by mutableStateOf(false)
    var selecionado by mutableStateOf<String?>(null)
    var arrastando by mutableStateOf(false)
    val apertados = mutableStateMapOf<String, Boolean>()

    private var dedoAnalogico: PointerId? = null
    private var origem = Offset.Zero
    private val dedos = HashMap<PointerId, String>()
    private val segurando = HashMap<String, Int>()
    private val direcoes = HashMap<String, Boolean>()
    private var dedoEdicao: PointerId? = null
    private var pega = Offset.Zero

    fun centroAgora(): Offset = if (centro.isSpecified) centro else centroPadrao

    /** A geometria mudou (tela, modo ou ajustes): o analógico volta ao lugar dele. */
    fun novaGeometria(c: Any) {
        if (c == chave) return
        chave = c
        if (dedoAnalogico == null) centro = Offset.Unspecified
    }

    fun desceu(id: PointerId, p: Offset) {
        if (editando) {
            editarDesceu(id, p)
            return
        }
        if (zonaAnalogico.contains(p)) {
            if (inclinando) {
                toque()
                aoZerar()
                return
            }
            if (dedoAnalogico != null) return
            dedoAnalogico = id
            if (!fixo) centro = encaixar(zonaAnalogico, tamBase, k, p)
            origem = centroAgora()
            vivo = true
            moverAnalogico(p)
        } else if (zonaBotoes.contains(p)) {
            mudarDedo(id, escolher(p, null))
        }
    }

    fun moveu(id: PointerId, p: Offset) {
        if (editando) {
            editarMoveu(id, p)
            return
        }
        if (id == dedoAnalogico) moverAnalogico(p)
        else dedos[id]?.let { atual -> mudarDedo(id, escolher(p, atual)) }
    }

    fun subiu(id: PointerId) {
        if (editando) {
            if (id == dedoEdicao) {
                dedoEdicao = null
                arrastando = false
            }
            return
        }
        if (id == dedoAnalogico) soltarAnalogico() else mudarDedo(id, null)
    }

    /** Nenhum dedo na tela: garante que nada ficou segurado. */
    fun semDedos() {
        if (dedoAnalogico != null) soltarAnalogico()
        for (id in dedos.keys.toList()) mudarDedo(id, null)
        dedoEdicao = null
        arrastando = false
    }

    /** Solta tudo (abrir os ajustes, trocar de tela, app para o fundo). */
    fun soltarTudo() {
        dedos.clear()
        segurando.clear()
        apertados.clear()
        direcoes.clear()
        dedoAnalogico = null
        dedoEdicao = null
        arrastando = false
        vivo = false
        correndo = false
        pino = Offset.Zero
        entrada.soltarTudo()
    }

    // analógico

    private fun moverAnalogico(p: Offset) {
        val r = tamBase / 2f
        val d = p - origem
        val dist = d.getDistance()
        val max = r * 0.75f
        val f = if (dist > max) max / dist else 1f
        pino = d * f
        val nx = if (dist > 0f) d.x / dist else 0f
        val ny = if (dist > 0f) d.y / dist else 0f
        val ativo = dist > r * 0.18f
        correr(futebol && dist > r)
        val forca = if (ativo) min(1f, (dist - r * 0.18f) / (max - r * 0.18f)) else 0f
        entrada.eixo(nx * forca, ny * forca)
        direcao("left", ativo && nx < -0.38f)
        direcao("right", ativo && nx > 0.38f)
        direcao("up", ativo && ny < -0.38f)
        direcao("down", ativo && ny > 0.38f)
    }

    /** O sensor de INCLINAR mexeu (x e y de -1 a 1; ``forte`` = inclinou muito). */
    fun inclinar(nx: Float, ny: Float, forte: Boolean) {
        if (editando || !inclinando || dedoAnalogico != null) return
        val d = hypot(nx, ny)
        val max = tamBase / 2f * 0.75f
        pino = Offset(nx, ny) * max
        vivo = d > 0f
        val ux = if (d > 0f) nx / d else 0f
        val uy = if (d > 0f) ny / d else 0f
        correr(futebol && forte)
        entrada.eixo(nx, ny)
        direcao("left", d > 0f && ux < -0.38f)
        direcao("right", d > 0f && ux > 0.38f)
        direcao("up", d > 0f && uy < -0.38f)
        direcao("down", d > 0f && uy > 0.38f)
    }

    /** O sensor desligou: o analógico volta ao centro. */
    fun pararDeInclinar() {
        if (dedoAnalogico == null) soltarAnalogico()
    }

    private fun soltarAnalogico() {
        dedoAnalogico = null
        pino = Offset.Zero
        vivo = false
        for (d in listOf("left", "right", "up", "down")) direcao(d, false)
        correr(false)
        entrada.eixo(0f, 0f)
    }

    private fun correr(sim: Boolean) {
        if (correndo == sim) return
        correndo = sim
        if (sim) {
            entrada.apertar("sprint")
            aoCorrer()
        } else {
            entrada.soltar("sprint")
        }
    }

    private fun direcao(nome: String, sim: Boolean) {
        if ((direcoes[nome] ?: false) == sim) return
        direcoes[nome] = sim
        if (sim) entrada.apertar(nome) else entrada.soltar(nome)
    }

    // botões

    private fun distanciaDaBorda(b: PosBotao, p: Offset): Float = hypot(p.x - b.x, p.y - b.y) - b.tam / 2f

    private fun escolher(p: Offset, atual: String?): String? {
        var melhor: PosBotao? = null
        var md = Float.MAX_VALUE
        for (b in botoes) {
            val d = distanciaDaBorda(b, p)
            if (d < md) {
                md = d
                melhor = b
            }
        }
        if (atual != null) {
            if (melhor != null && melhor.def.acao != atual && md <= 0f) return melhor.def.acao   // entrou em outro botão
            val eu = botoes.firstOrNull { it.def.acao == atual } ?: return null
            return if (distanciaDaBorda(eu, p) <= SEGURA * k) atual else null
        }
        return if (md <= IMA * k) melhor?.def?.acao else null
    }

    private fun mudarDedo(id: PointerId, acao: String?) {
        val antes = dedos[id]
        if (antes == acao) return
        if (antes != null) largar(antes)
        if (acao != null) {
            pegar(acao)
            toque()
            dedos[id] = acao
        } else {
            dedos.remove(id)
        }
    }

    private fun pegar(acao: String) {
        val n = (segurando[acao] ?: 0) + 1
        segurando[acao] = n
        if (n == 1) {
            apertados[acao] = true
            entrada.apertar(acao)
        }
    }

    private fun largar(acao: String) {
        val n = max(0, (segurando[acao] ?: 0) - 1)
        segurando[acao] = n
        if (n == 0) {
            apertados.remove(acao)
            entrada.soltar(acao)
        }
    }

    // AJUSTES DO CONTROLE: arrastar

    private fun editarDesceu(id: PointerId, p: Offset) {
        if (zonaBotoes.contains(p)) {
            val a = escolher(p, null)
            selecionado = a
            if (a != null) {
                toque()
                dedoEdicao = id
                arrastando = true
                val b = botoes.first { it.def.acao == a }
                pega = Offset(p.x - b.x, p.y - b.y)
            }
        } else if (zonaAnalogico.contains(p)) {
            toque()
            selecionado = "stick"
            dedoEdicao = id
            arrastando = true
            val c = centroAgora()
            pega = if ((p - c).getDistance() <= tamBase / 2f + 10f * k) p - c else Offset.Zero
            editarMoveu(id, p)
        } else {
            selecionado = null
        }
    }

    private fun editarMoveu(id: PointerId, p: Offset) {
        if (id != dedoEdicao) return
        val sel = selecionado ?: return
        val alvo = p - pega
        if (sel == "stick") {
            val za = zonaAnalogico
            val c = encaixar(za, tamBase, k, alvo)
            mudarHud(hud.copy(analogico = Offset((c.x - za.left) / za.width, (c.y - za.top) / za.height)))
        } else {
            val zb = zonaBotoes
            val x = ((alvo.x - zb.left) / zb.width).coerceIn(0f, 1f)
            val y = ((alvo.y - zb.top) / zb.height).coerceIn(0f, 1f)
            mudarHud(hud.comBotao(sel) { it.copy(x = x, y = y) })
        }
    }
}

// ── a tela do controle ────────────────────────

/** O controle do modo (analógico + botões em arco), com a barra de cima e os AJUSTES DO CONTROLE. */
@Composable
fun TelaControle(st: Status, me: Me) {
    val app = LocalApp.current
    val canal = app.canal
    val m = LocalMedidas.current
    val rapido = canal.rapido
    val perfil = perfilDoModo(st.modo, st.hud)
    val heroi = canal.roster.getOrNull(me.personagem)
    val mao = me.mao

    var salvo by remember(perfil) { mutableStateOf(Hud.carregar(app.prefs.hud(perfil))) }
    var rascunho by remember(perfil) { mutableStateOf<Hud?>(null) }
    var recado by remember(perfil) { mutableStateOf("") }
    var painelEmbaixo by remember { mutableStateOf(false) }
    val editando = rascunho != null
    val hud = rascunho ?: salvo

    val pad = remember { Pad(canal.entrada) }
    DisposableEffect(pad) { onDispose { pad.soltarTudo() } }
    BackHandler(enabled = editando) {
        rascunho = null
        pad.selecionado = null
    }

    // MAPA (e CADERNO) e o balão de reações, por cima do controle
    var mapaAberto by remember { mutableStateOf(false) }
    var reacoesAbertas by remember { mutableStateOf(false) }
    var equipeAberta by remember { mutableStateOf(false) }
    LaunchedEffect(me.podeChamar) { if (!me.podeChamar) equipeAberta = false }
    LaunchedEffect(st.temMapa) { if (!st.temMapa) mapaAberto = false }
    BackHandler(enabled = mapaAberto) { mapaAberto = false }

    // INCLINAR: o sensor só fica ligado com o controle na tela e o app na frente
    var semSensor by remember { mutableStateOf(false) }
    val inclinando = hud.inclinar && !editando && !mapaAberto && app.naFrente
    val vista = LocalView.current
    DisposableEffect(inclinando) {
        if (!inclinando) return@DisposableEffect onDispose {}
        val sensor = Inclinacao(app.contexto, { vista.display?.rotation ?: Surface.ROTATION_90 }) { x, y, forte ->
            pad.inclinar(x, y, forte)
        }
        pad.aoZerar = { sensor.zerar() }
        semSensor = !sensor.ligar()
        pad.inclinando = !semSensor
        onDispose {
            sensor.desligar()
            pad.inclinando = false
            pad.aoZerar = {}
            pad.pararDeInclinar()
        }
    }

    val defs = remember(perfil, heroi, mao) { botoesDoModo(perfil, heroi, mao) }
    val aneis = aneisDoModo(perfil, rapido)
    val contador = contadorDoModo(perfil, rapido)
    val futebol = perfil == "futebol" || perfil == "basquete"

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val w = constraints.maxWidth.toFloat()
        val h = constraints.maxHeight.toFloat()
        val k = m.k.toFloat()
        val zb = if (hud.canhoto) Rect(0f, 52f * k, w * 0.48f, h) else Rect(w * 0.52f, 52f * k, w, h)
        val za = if (hud.canhoto) Rect(w * 0.5f, 0f, w, h) else Rect(0f, 0f, w * 0.5f, h)
        val posicoes = posicoesDosBotoes(defs, zb, h, k, hud)
        val baseJogo = if (h / k <= 360f) 120f else 140f
        val tamBase = (baseJogo * hud.escalaAnalogico).roundToInt() * k
        val tamPino = (56f * hud.escalaAnalogico).roundToInt() * k
        val ana = hud.analogico
        val centroPadrao = if (ana != null) {
            encaixar(za, tamBase, k, Offset(za.left + ana.x * za.width, za.top + ana.y * za.height))
        } else {
            Offset(
                if (hud.canhoto) za.right - 42f * k - tamBase / 2f else za.left + 42f * k + tamBase / 2f,
                za.bottom - 40f * k - tamBase / 2f,
            )
        }

        SideEffect {
            pad.botoes = posicoes
            pad.zonaBotoes = zb
            pad.zonaAnalogico = za
            pad.k = k
            pad.tamBase = tamBase
            pad.centroPadrao = centroPadrao
            pad.futebol = futebol
            pad.fixo = hud.fixo
            pad.editando = editando
            pad.inclinando = inclinando && !semSensor
            pad.hud = hud
            pad.toque = { app.toque() }
            pad.aoCorrer = { app.vibrador.tocar("correr") }
            pad.mudarHud = { novo -> rascunho = novo }
            pad.novaGeometria(listOf(w, h, hud, perfil))
        }

        // os dedos e o que eles apertam
        Box(
            Modifier
                .fillMaxSize()
                .pointerInput(pad) {
                    awaitPointerEventScope {
                        while (true) {
                            val ev = awaitPointerEvent()
                            for (c in ev.changes) {
                                when {
                                    c.changedToDownIgnoreConsumed() -> pad.desceu(c.id, c.position)
                                    c.changedToUpIgnoreConsumed() -> pad.subiu(c.id)
                                    c.pressed && c.positionChangedIgnoreConsumed() -> pad.moveu(c.id, c.position)
                                }
                                c.consume()
                            }
                            if (ev.changes.none { it.pressed }) pad.semDedos()
                        }
                    }
                }
        ) {
            Analogico(
                pad = pad,
                tam = tamBase,
                tamPino = tamPino,
                vaga = me.vaga,
                opacidade = hud.opacidade,
                folego = if (futebol) rapido.stamina else null,
                cansado = rapido.cansado,
                contorno = when {
                    !editando -> null
                    pad.selecionado == "stick" -> Cores.Brass
                    else -> Cores.LineHi
                },
            )
            for (b in posicoes) {
                BotaoDoPad(
                    b = b,
                    apertado = pad.apertados[b.def.acao] == true,
                    vaga = me.vaga,
                    anel = aneis[b.def.acao],
                    opacidade = hud.opacidade,
                    contorno = when {
                        !editando -> null
                        pad.selecionado == b.def.acao -> Cores.Brass
                        else -> Cores.LineHi
                    },
                )
            }
        }

        // munição / energia em cima do botão grande
        val principal = posicoes.firstOrNull { it.def.pos == "main" }
        if (contador != null && principal != null) {
            ContadorDeMunicao(contador, principal.x, max(0f, principal.y - principal.tam / 2f - 22f * k - zb.top) + zb.top)
        }

        if (!editando) {
            Box(
                Modifier
                    .fillMaxSize()
                    .padding(horizontal = 12.u, vertical = 10.u),
                contentAlignment = if (hud.canhoto) Alignment.BottomEnd else Alignment.BottomStart,
            ) {
                Texto(
                    when {
                        hud.inclinar && semSensor -> "este celular não tem sensor de inclinar: use o analógico"
                        hud.inclinar -> "incline o celular · toque aqui para zerar"
                        else -> dicaDoModo(perfil)
                    },
                    cor = Cores.Muted,
                )
            }
            BarraDoControle(
                st = st,
                me = me,
                rapido = rapido,
                aoAjustes = {
                    pad.soltarTudo()
                    pad.selecionado = null
                    recado = ""
                    reacoesAbertas = false
                    equipeAberta = false
                    rascunho = salvo
                },
                aoMapa = if (st.temMapa) {
                    {
                        pad.soltarTudo()
                        reacoesAbertas = false
                        equipeAberta = false
                        mapaAberto = true
                    }
                } else null,
                aoReacoes = if (st.temExtras) {
                    {
                        equipeAberta = false
                        reacoesAbertas = !reacoesAbertas
                    }
                } else null,
                aoEquipe = if (me.podeChamar) {
                    {
                        reacoesAbertas = false
                        equipeAberta = !equipeAberta
                    }
                } else null,
            )
            if (me.chamadas.isNotEmpty() && !equipeAberta && !reacoesAbertas) {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(top = 48.u),
                    contentAlignment = Alignment.TopCenter,
                ) {
                    AvisoDaEquipe(me.chamadas)
                }
            }
            if (equipeAberta) {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(top = 44.u, end = 12.u),
                    contentAlignment = Alignment.TopEnd,
                ) {
                    PainelDaEquipe(aoFechar = { equipeAberta = false })
                }
            }
            if (reacoesAbertas) {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(top = 44.u, end = 12.u),
                    contentAlignment = Alignment.TopEnd,
                ) {
                    PainelDeReacoes(aoFechar = { reacoesAbertas = false })
                }
            }
        } else {
            val r = rascunho ?: salvo
            val sel = pad.selecionado
            val nomeSel = when (sel) {
                null -> null
                "stick" -> "ANALÓGICO"
                else -> defs.firstOrNull { it.acao == sel }?.rotulo ?: sel.uppercase()
            }
            val escala = when (sel) {
                null -> null
                "stick" -> r.escalaAnalogico
                else -> r.botoes[sel]?.s ?: 1f
            }
            DicaDosAjustes(
                texto = recado.ifEmpty {
                    if (nomeSel != null) "$nomeSel: ARRASTE PARA MUDAR DE LUGAR. O TAMANHO MUDA SÓ ELE."
                    else "CADA MODO (DUELO, FUTEBOL, BASQUETE E CAMPANHA) GUARDA O SEU JEITO DE BOTÕES."
                },
                embaixo = painelEmbaixo,
                apagada = pad.arrastando,
            )
            PainelDosAjustes(
                hud = r,
                perfil = perfil,
                nomeSel = nomeSel,
                escala = escala,
                embaixo = painelEmbaixo,
                apagado = pad.arrastando,
                aoMudar = { rascunho = it },
                aoTamanho = { passo ->
                    val atual = rascunho ?: salvo
                    rascunho = when (sel) {
                        null -> atual
                        "stick" -> atual.copy(escalaAnalogico = arredondar((atual.escalaAnalogico + passo).coerceIn(0.7f, 1.5f)))
                        else -> atual.comBotao(sel) { it.copy(s = arredondar((it.s + passo).coerceIn(0.7f, 1.5f))) }
                    }
                },
                aoTestar = { recado = testarVibracao(app, me.vibracaoNoJogo) },
                aoVibracao = { recado = "" },
                aoMoverPainel = { painelEmbaixo = !painelEmbaixo },
                aoRestaurar = {
                    rascunho = Hud()
                    pad.selecionado = null
                },
                aoCancelar = {
                    rascunho = null
                    pad.selecionado = null
                },
                aoSalvar = {
                    val novo = rascunho ?: salvo
                    app.prefs.salvarHud(perfil, novo.json())
                    salvo = novo
                    rascunho = null
                    pad.selecionado = null
                },
            )
        }

        if (st.fase == "paused" && !editando && !mapaAberto) Pausado()
        if (mapaAberto) TelaMapa(me.vaga, aoFechar = { mapaAberto = false })
    }
}

// ── analógico ─────────────────────────────────

@Composable
private fun Analogico(
    pad: Pad,
    tam: Float,
    tamPino: Float,
    vaga: Int,
    opacidade: Float,
    folego: Float?,
    cansado: Boolean,
    contorno: Color?,
) {
    val m = LocalMedidas.current
    val margem = m.px(MARGEM)
    val lado = tam + 2f * margem
    val cor = corVaga(vaga)
    val escura = corVagaEscura(vaga)
    Spacer(
        Modifier
            .layout { med, _ ->
                val s = lado.roundToInt()
                val p = med.measure(Constraints.fixed(s, s))
                layout(s, s) {
                    val c = pad.centroAgora()
                    p.place((c.x - lado / 2f).roundToInt(), (c.y - lado / 2f).roundToInt())
                }
            }
            .graphicsLayer { alpha = opacidade }
            .drawBehind {
                val u = m.px(1)
                val c = Offset(size.width / 2f, size.height / 2f)
                val r = tam / 2f
                // anel do fôlego (futebol e basquete): enche verde, fica vermelho cansado
                if (folego != null) {
                    val rr = r + 8.5f * u
                    drawCircle(Cores.Line, rr, c, style = Stroke(5f * u))
                    drawArc(
                        if (cansado) Cores.Blood else Cores.Moss, -90f, 360f * folego.coerceIn(0f, 1f), false,
                        topLeft = Offset(c.x - rr, c.y - rr), size = Size(rr * 2f, rr * 2f), style = Stroke(5f * u),
                    )
                }
                drawCircle(Cores.Edge, r + 3f * u, c)
                drawCircle(Color(0xFF120F20), r, c)
                drawCircle(Color(0xFF1A1530), r * 0.778f, c)
                drawCircle(Cores.Edge, r - 4f * u, c, style = Stroke(8f * u))
                drawCircle(if (pad.vivo) escura else Color(0xFF2A2340), r - 3f * u, c, style = Stroke(6f * u))
                // marquinhas das 8 direções
                val rm = r - 14f * u
                val rt = rm * 0.95f
                for (i in 0 until 8) {
                    drawArc(
                        Cores.LineHi, -94f + 45f * i, 8f, false,
                        topLeft = Offset(c.x - rt, c.y - rt), size = Size(rt * 2f, rt * 2f), style = Stroke(rm * 0.1f),
                    )
                }
                if (contorno != null) tracejadoRedondo(contorno, c, r + 6f * u, u)
                // o pino
                val pc = c + pad.pino
                val rp = tamPino / 2f
                drawCircle(Color.Black.copy(alpha = 0.4f), rp + 2f * u, pc + Offset(0f, 4f * u))
                drawCircle(Cores.Edge, rp + 3f * u, pc)
                val brilho = if (pad.correndo) {
                    Brush.radialGradient(
                        0f to Color(0xFFB8F5C8), 0.5f to Cores.Moss, 0.85f to Color(0xFF1D6A34),
                        center = pc + Offset(-0.15f * tamPino, -0.2f * tamPino), radius = tamPino * 0.955f,
                    )
                } else {
                    Brush.radialGradient(
                        0f to mistura(cor, 0.55f, Color.White), 0.5f to cor, 0.85f to escura,
                        center = pc + Offset(-0.15f * tamPino, -0.2f * tamPino), radius = tamPino * 0.955f,
                    )
                }
                drawCircle(brilho, rp, pc)
                val sombra = Path.combine(
                    PathOperation.Difference,
                    Path().apply { addOval(Rect(pc, rp)) },
                    Path().apply { addOval(Rect(pc + Offset(0f, -4f * u), rp)) },
                )
                drawPath(sombra, Color.Black.copy(alpha = 0.35f))
            }
    )
}

/** Contorno tracejado redondo (o que dá para arrastar nos AJUSTES DO CONTROLE). */
private fun DrawScope.tracejadoRedondo(cor: Color, c: Offset, r: Float, u: Float) {
    drawCircle(
        cor, r, c,
        style = Stroke(2f * u, pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f * u, 4f * u))),
    )
}

// ── um botão do arco ──────────────────────────

@Composable
private fun BotaoDoPad(
    b: PosBotao,
    apertado: Boolean,
    vaga: Int,
    anel: Anel?,
    opacidade: Float,
    contorno: Color?,
) {
    val m = LocalMedidas.current
    val d = b.def
    val local = ImageBitmap.imageResource(d.icone)
    val remota = imagemDoJogo(d.desenhoDoJogo)
    val tam = b.tam
    val margem = m.px(MARGEM)
    val larguraNome = m.px(d.rotulo.length * 8 + 12)
    val largura = max(tam + 2f * margem, larguraNome)
    val altura = tam + 2f * margem
    val cor = corVaga(vaga)
    val (corA, corB, parada) = when (d.estilo) {
        EstiloBotao.PRINCIPAL -> Triple(mistura(cor, 0.7f, Color.White), corVagaEscura(vaga), 0.75f)
        EstiloBotao.MARCAR -> Triple(Color(0xFF6A2A2A), Color(0xFF2A1414), 0.72f)
        EstiloBotao.HABILIDADE, EstiloBotao.SUPER -> Triple(Color(0xFF6A4A1A), Color(0xFF2A1D0A), 0.72f)
        EstiloBotao.NORMAL -> Triple(Color(0xFF3A3258), Color(0xFF1C1730), 0.7f)
    }
    val tamIcone = if (tam / m.k >= 96f) 48 else 32
    val cinza = anel?.apagado == true && d.estilo == EstiloBotao.SUPER
    Box(
        Modifier
            .layout { med, _ ->
                val wi = largura.roundToInt()
                val hi = altura.roundToInt()
                val p = med.measure(Constraints.fixed(wi, hi))
                layout(wi, hi) { p.place((b.x - largura / 2f).roundToInt(), (b.y - altura / 2f).roundToInt()) }
            }
            .graphicsLayer {
                alpha = opacidade
                translationY = if (apertado) m.px(4) else 0f
            }
            .drawWithCache {
                val u = m.px(1)
                val c = Offset(size.width / 2f, size.height / 2f)
                val r = tam / 2f
                val luz = Path.combine(
                    PathOperation.Difference,
                    Path().apply { addOval(Rect(c, r)) },
                    Path().apply { addOval(Rect(c + Offset(0f, 3f * u), r)) },
                )
                val sombra = Path.combine(
                    PathOperation.Difference,
                    Path().apply { addOval(Rect(c, r)) },
                    Path().apply { addOval(Rect(c + Offset(0f, -5f * u), r)) },
                )
                val fundo = Brush.radialGradient(
                    0f to corA, parada to corB,
                    center = Offset(c.x - r + 0.35f * tam, c.y - r + 0.3f * tam), radius = tam * 0.955f,
                )
                onDrawBehind {
                    drawCircle(Color.Black.copy(alpha = 0.4f), r + 2f * u, c + Offset(0f, (if (apertado) 1f else 5f) * u))
                    drawCircle(Cores.Edge, r + 3f * u, c)
                    if (anel != null) {
                        val ra = r + 5.5f * u
                        drawCircle(Cores.Line, ra, c, style = Stroke(5f * u))
                        drawArc(
                            anel.cor, -90f, 360f * anel.p, false,
                            topLeft = Offset(c.x - ra, c.y - ra), size = Size(ra * 2f, ra * 2f), style = Stroke(5f * u),
                        )
                        if (anel.pronto) drawCircle(Cores.Brass.copy(alpha = 0.35f), r + 9.5f * u, c, style = Stroke(3f * u))
                    }
                    drawCircle(fundo, r, c)
                    drawPath(luz, Color.White.copy(alpha = if (apertado) 0.1f else 0.18f))
                    if (!apertado) drawPath(sombra, Color.Black.copy(alpha = 0.45f))
                    // o desenho: a arma da mão (do jogo) ou o ícone do botão, em escala inteira
                    val img = remota ?: local
                    val n = max(img.width, img.height).toFloat()
                    val esc = if (n <= tamIcone) floor(tamIcone / n) else 1f / ceil(n / tamIcone)
                    val iw = img.width * esc * m.k
                    val ih = img.height * esc * m.k
                    val ix = (c.x - iw / 2f).roundToInt().toFloat()
                    val iy = (c.y - ih / 2f).roundToInt().toFloat()
                    desenharPixel(img, ix + 2f * u, iy + 2f * u, iw, ih, 1f, ColorFilter.tint(Color(0x99000000), BlendMode.SrcIn))
                    desenharPixel(img, ix, iy, iw, ih, 1f, if (cinza) filtroCinza(0.6f) else null)
                    if (contorno != null) tracejadoRedondo(contorno, c, r + 6f * u, u)
                }
            }
    ) {
        // a plaquinha do nome, presa na borda de baixo
        Box(
            Modifier
                .align(Alignment.TopCenter)
                .deslocado { IntOffset(0, (margem + tam - m.px(7)).roundToInt()) }
                .wrapContentWidth(unbounded = true)
                .drawBehind {
                    val u = m.px(1)
                    drawRect(
                        if (d.estilo == EstiloBotao.PRINCIPAL) cor else Cores.LineHi,
                        Offset(-u, -u), Size(size.width + 2f * u, size.height + 2f * u),
                    )
                    drawRect(Cores.Edge)
                }
                .padding(start = 4.u, end = 4.u, top = 2.u)
        ) {
            Texto(d.rotulo, cor = if (apertado) Cores.Brass else Cores.Bone, linhas = 1, linha = 10)
        }
    }
}

private fun Modifier.deslocado(deslocar: () -> IntOffset): Modifier = layout { med, c ->
    val p = med.measure(c)
    layout(p.width, p.height) { p.place(deslocar()) }
}

/** RECARGA, VAZIO, 12/30, ENERGIA 40... em cima do botão grande. */
@Composable
private fun ContadorDeMunicao(c: Contador, x: Float, y: Float) {
    val m = LocalMedidas.current
    val borda = when {
        c.vazio -> Cores.Blood
        c.recarga -> Cores.Brass
        else -> Cores.LineHi
    }
    val cor = when {
        c.vazio -> Color(0xFFF0A49E)
        c.recarga -> Cores.Brass
        else -> Cores.Bone
    }
    Box(
        Modifier
            .layout { med, _ ->
                val p = med.measure(Constraints())
                layout(p.width, p.height) { p.place((x - p.width / 2f).roundToInt(), y.roundToInt()) }
            }
            .drawBehind {
                val e = m.px(2)
                drawRect(borda, Offset(-e, -e), Size(size.width + 2f * e, size.height + 2f * e))
                drawRect(Cores.Edge)
            }
            .padding(start = 6.u, end = 6.u, top = 3.u, bottom = 1.u)
    ) {
        Texto(c.texto, cor = cor, linhas = 1, linha = 8)
    }
}

// ── barra de cima ─────────────────────────────

@Composable
private fun BarraDoControle(
    st: Status,
    me: Me,
    rapido: Rapido,
    aoAjustes: () -> Unit,
    aoMapa: (() -> Unit)?,
    aoReacoes: (() -> Unit)?,
    aoEquipe: (() -> Unit)?,
) {
    val app = LocalApp.current
    val canal = app.canal
    var nome = nomeDoModo(st.modo, st.hud)
    val time = me.time
    if (st.modo != "campaign" && (time == 0 || time == 1)) nome += " · TIME " + if (time == 0) "AZUL" else "VERMELHO"
    Cabecalho(Modifier.bloquearToques()) {
        Tag(me.vaga, me.personagem)
        Texto(nome, Modifier.weight(1f, fill = false), cor = Cores.Muted, linhas = 1)
        val almas = rapido.almas
        if (st.modo == "campaign" && almas != null) Almas(almas)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.u)) {
            Sinal(canal.rtt, Modifier.size(16.u))
            Texto(if (canal.rtt >= 0) "${canal.rtt} MS" else "-- MS", cor = corDoSinal(canal.rtt), linhas = 1)
        }
        Spacer(Modifier.weight(1f))
        if (aoEquipe != null) Botao("EQUIPE", altura = 28, naHora = true) { aoEquipe() }
        if (aoReacoes != null) Botao("", icone = R.drawable.r_kkk, altura = 28, naHora = true) { aoReacoes() }
        if (aoMapa != null) Botao("MAPA", altura = 28) { aoMapa() }
        Botao("AJUSTES", altura = 28) { aoAjustes() }
        Botao("II", altura = 28, naHora = true) { canal.entrada.tocar("pause") }
    }
}

/** Saldo de almas da campanha: quando muda, um "+N" sobe ao lado e a pílula pula. */
@Composable
private fun Almas(n: Int) {
    val m = LocalMedidas.current
    var antes by remember { mutableStateOf<Int?>(null) }
    var ganho by remember { mutableIntStateOf(0) }
    var vez by remember { mutableIntStateOf(0) }
    val sobe = remember { Animatable(1f) }
    val pulo = remember { Animatable(1f) }
    LaunchedEffect(n) {
        val a = antes
        if (a != null && a != n) {
            ganho = n - a
            vez += 1
        }
        antes = n
    }
    LaunchedEffect(vez) {
        if (vez == 0) return@LaunchedEffect
        launch {
            pulo.snapTo(1.15f)
            pulo.animateTo(1f, tween(260))
        }
        sobe.snapTo(0f)
        sobe.animateTo(1f, tween(900, easing = LinearOutSlowInEasing))
    }
    Box {
        Pilula(
            R.drawable.i_alma, "$n", Cores.Soul,
            Modifier.graphicsLayer {
                scaleX = pulo.value
                scaleY = pulo.value
            },
        )
        if (vez > 0 && sobe.value < 1f) {
            Texto(
                (if (ganho > 0) "+" else "") + ganho,
                Modifier
                    .align(Alignment.TopEnd)
                    .layout { med, _ ->
                        val p = med.measure(Constraints())
                        layout(0, 0) { p.place(m.px(6).roundToInt(), (m.px(4) - sobe.value * m.px(16)).roundToInt()) }
                    }
                    .graphicsLayer { alpha = 1f - sobe.value },
                cor = if (ganho < 0) Color(0xFFF0A49E) else Cores.Soul,
                linhas = 1,
            )
        }
    }
}

// ── pausado ───────────────────────────────────

/** Jogo pausado: o menu está na TV e dá para mexer nele daqui (quem manda na partida). */
@Composable
private fun Pausado() {
    val app = LocalApp.current
    val entrada = app.canal.entrada
    Sobreposicao(escurecer = 0.82f) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.u)) {
            Texto("PAUSADO", tam = 24, cor = Cores.Brass, sombra = true)
            Texto("O MENU ESTÁ NA TV. QUEM MANDA NA PARTIDA ESCOLHE DAQUI:", cor = Cores.Muted, alinhar = TextAlign.Center)
            Row(horizontalArrangement = Arrangement.spacedBy(8.u), verticalAlignment = Alignment.CenterVertically) {
                for ((rotulo, acao) in listOf("▲" to "up", "▼" to "down", "◀" to "left", "▶" to "right")) {
                    Botao(rotulo, tam = 16, naHora = true, altura = 40) { entrada.tocar(acao) }
                }
                Spacer(Modifier.size(8.u))
                Botao("OK", tipo = TipoBotao.VERDE, tam = 16, naHora = true, altura = 40) { entrada.tocar("confirm") }
                Botao("VOLTAR", naHora = true, altura = 40) { entrada.tocar("cancel") }
            }
            Botao("CONTINUAR", tipo = TipoBotao.DOURADO, tam = 16, naHora = true, altura = 40) { entrada.tocar("pause") }
        }
    }
}

// ── AJUSTES DO CONTROLE ───────────────────────

/** O balãozinho de papel com a dica (ou o que o TESTAR respondeu). */
@Composable
private fun DicaDosAjustes(texto: String, embaixo: Boolean, apagada: Boolean) {
    val m = LocalMedidas.current
    BoxWithConstraints(
        Modifier
            .fillMaxSize()
            .padding(vertical = 24.u),
        contentAlignment = if (embaixo) Alignment.TopCenter else Alignment.BottomCenter,
    ) {
        Box(
            Modifier
                .widthIn(max = maxWidth * 0.34f)
                .graphicsLayer { alpha = if (apagada) 0.35f else 1f }
                .moldura(m, fundo = Cores.Papel, luz = Color.White, sombra = Color(0xFFC9BFA5))
                .padding(horizontal = 10.u, vertical = 6.u)
        ) {
            Texto(texto, cor = Cores.Tinta)
        }
    }
}

@Composable
private fun PainelDosAjustes(
    hud: Hud,
    perfil: String,
    nomeSel: String?,
    escala: Float?,
    embaixo: Boolean,
    apagado: Boolean,
    aoMudar: (Hud) -> Unit,
    aoTamanho: (Float) -> Unit,
    aoTestar: () -> Unit,
    aoVibracao: () -> Unit,
    aoMoverPainel: () -> Unit,
    aoRestaurar: () -> Unit,
    aoCancelar: () -> Unit,
    aoSalvar: () -> Unit,
) {
    val app = LocalApp.current
    val m = LocalMedidas.current
    Box(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 12.u, vertical = 8.u),
        contentAlignment = if (embaixo) Alignment.BottomCenter else Alignment.TopCenter,
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .graphicsLayer { alpha = if (apagado) 0.3f else 1f }
                .moldura(m, fundo = Color(0xFF141026))
                .bloquearToques()
                .padding(8.u),
            verticalArrangement = Arrangement.spacedBy(6.u),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.u)) {
                Texto("AJUSTES DO CONTROLE · ARRASTE OS BOTÕES PARA MOVER", Modifier.weight(1f), cor = Cores.Brass, linhas = 1)
                Texto("FICA SALVO NO CELULAR", cor = Cores.Muted, linhas = 1)
                Botao(if (embaixo) "▲ PAINEL" else "▼ PAINEL", altura = 20, naHora = true) { aoMoverPainel() }
            }
            Row(Modifier.fillMaxWidth().height(44.u), horizontalArrangement = Arrangement.spacedBy(8.u)) {
                CartaoAjuste("TAMANHO", Modifier.weight(1f)) {
                    if (escala == null || nomeSel == null) {
                        Texto("TOQUE EM UM BOTÃO", cor = Cores.Dim, linhas = 1)
                    } else {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.u)) {
                            Botao("-", altura = 20, naHora = true, ativo = escala > 0.7f) { aoTamanho(-0.1f) }
                            Texto("${(escala * 100).roundToInt()}%", cor = Cores.Bone, linhas = 1)
                            Botao("+", altura = 20, naHora = true, ativo = escala < 1.5f) { aoTamanho(0.1f) }
                        }
                    }
                }
                CartaoAjuste("OPACIDADE", Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.u)) {
                        Botao("-", altura = 20, naHora = true, ativo = hud.opacidade > 0.3f) {
                            aoMudar(hud.copy(opacidade = arredondar((hud.opacidade - 0.1f).coerceIn(0.3f, 1f))))
                        }
                        Texto("${(hud.opacidade * 100).roundToInt()}%", cor = Cores.Bone, linhas = 1)
                        Botao("+", altura = 20, naHora = true, ativo = hud.opacidade < 1f) {
                            aoMudar(hud.copy(opacidade = arredondar((hud.opacidade + 0.1f).coerceIn(0.3f, 1f))))
                        }
                    }
                }
                // SOLTO > FIXO > INCLINAR (andar inclinando o celular) > SOLTO
                CartaoAjuste(
                    "ANALÓGICO", Modifier.weight(1f),
                    aoApertar = {
                        aoMudar(
                            when {
                                hud.inclinar -> hud.copy(inclinar = false, fixo = false)
                                hud.fixo -> hud.copy(fixo = false, inclinar = true)
                                else -> hud.copy(fixo = true)
                            }
                        )
                    },
                    ligado = hud.inclinar,
                ) {
                    Texto(
                        when {
                            hud.inclinar -> "INCLINAR"
                            hud.fixo -> "FIXO"
                            else -> "SOLTO"
                        },
                        cor = if (hud.inclinar) Cores.Moss else Cores.Muted, linhas = 1,
                    )
                }
                CartaoAjuste(
                    "CANHOTO", Modifier.weight(1f),
                    aoApertar = {
                        aoMudar(
                            hud.copy(
                                canhoto = !hud.canhoto,
                                botoes = hud.botoes.mapValues { (_, b) -> if (b.x != null) b.copy(x = 1f - b.x) else b },
                                analogico = null,
                            )
                        )
                    },
                    ligado = hud.canhoto,
                ) {
                    Texto(if (hud.canhoto) "SIM" else "NÃO", cor = if (hud.canhoto) Cores.Moss else Cores.Muted, linhas = 1)
                }
                CartaoAjuste(
                    "CLIQUE AO TOCAR", Modifier.weight(1f),
                    aoApertar = { app.mudarClique(!app.clique) },
                    ligado = app.clique,
                ) {
                    Texto(if (app.clique) "LIGADO" else "DESLIGADO", cor = if (app.clique) Cores.Moss else Cores.Muted, linhas = 1)
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.u),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(
                    Modifier
                        .weight(2.2f)
                        .moldura(m, fundo = Cores.Bolso, luz = Color.Black, sombra = Cores.Line)
                        .padding(6.u),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.u),
                ) {
                    Texto("VIBRAÇÃO", cor = Cores.Muted, linhas = 1)
                    SeletorVibracao(Modifier.weight(1f)) { aoVibracao() }
                }
                Botao("TESTAR", icone = R.drawable.i_vibrar, altura = 32) { aoTestar() }
                Row(
                    Modifier
                        .weight(1.2f)
                        .moldura(m, fundo = Cores.Bolso, luz = Color.Black, sombra = Cores.Line)
                        .padding(6.u),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.u),
                ) {
                    Texto("PERFIL", cor = Cores.Muted, linhas = 1)
                    Box(
                        Modifier
                            .weight(1f)
                            .height(32.u)
                            .moldura(m, fundo = Color(0xFF6B5418), luz = Color(0xFF8A6E22), sombra = Color(0xFF3A2C0C)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Texto(nomeDoPerfil(perfil), cor = Cores.Brass, linhas = 1)
                    }
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.u)) {
                Botao("RESTAURAR", Modifier.weight(1f), icone = R.drawable.i_trocar, altura = 40) { aoRestaurar() }
                Botao("CANCELAR", Modifier.weight(1.4f), tam = 16, altura = 40) { aoCancelar() }
                Botao("SALVAR", Modifier.weight(1.4f), tipo = TipoBotao.VERDE, tam = 16, altura = 40) { aoSalvar() }
            }
        }
    }
}

/** Um cartão da primeira linha dos ajustes: o nome em cima e o valor (ou os botões) embaixo. */
@Composable
private fun CartaoAjuste(
    titulo: String,
    modifier: Modifier = Modifier,
    aoApertar: (() -> Unit)? = null,
    ligado: Boolean = false,
    conteudo: @Composable () -> Unit,
) {
    val m = LocalMedidas.current
    val apertado = remember { mutableStateOf(false) }
    Column(
        modifier
            .fillMaxHeight()
            .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
            .moldura(m, fundo = if (ligado) Color(0xFF214A2E) else Cores.Ink3)
            .then(if (aoApertar != null) Modifier.aoTocar(apertado = apertado, acao = aoApertar) else Modifier)
            .padding(horizontal = 6.u, vertical = 4.u),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        Texto(titulo, cor = Cores.Bone, linhas = 1)
        conteudo()
    }
}
