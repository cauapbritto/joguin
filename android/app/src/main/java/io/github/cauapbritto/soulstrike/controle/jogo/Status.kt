package io.github.cauapbritto.soulstrike.controle.jogo

import org.json.JSONArray
import org.json.JSONObject

/*
 * O que o jogo manda para o celular (/api/status), igual ao que o site do controle recebe.
 * As lojas variam muito de formato (loja, ferreiro, altar, CACOS, armário, computador), então
 * ficam como JSON com leitores em volta, em vez de uma classe para cada.
 */

fun JSONObject.texto(nome: String, padrao: String = ""): String =
    if (has(nome) && !isNull(nome)) optString(nome, padrao) else padrao

fun JSONObject.textoOuNulo(nome: String): String? =
    if (has(nome) && !isNull(nome)) optString(nome).takeIf { it.isNotEmpty() } else null

fun JSONObject.inteiroOuNulo(nome: String): Int? =
    if (has(nome) && !isNull(nome)) (opt(nome) as? Number)?.toInt() else null

fun JSONArray?.objetos(): List<JSONObject> =
    if (this == null) emptyList() else (0 until length()).mapNotNull { optJSONObject(it) }

data class VagaInfo(val ocupada: Boolean, val conectada: Boolean)

/** Uma frase do botão EQUIPE de um colega: número, vaga de quem mandou, apelido (ou P2) e a frase. */
data class Chamada(val id: Int, val de: Int, val rotulo: String, val tipo: String)

data class PaginaNovidade(val indice: Int, val total: Int, val titulo: String)

data class Melhoria(val nome: String, val desc: String, val cor: Long)

data class Penalti(val papel: String, val heroi: String)

data class Mao(val nome: String, val icone: String)

/** O que muda a cada quadro: vem no pulso do canal rápido (ou no status, sem ele). */
data class Rapido(
    val cooldown: Float = 0f,
    val stamina: Float = 1f,
    val cansado: Boolean = false,
    val municao: Int = 0,
    val pente: Int = 0,
    val recarga: Float = 0f,
    val energia: Int = 0,
    val energiaMax: Int = 0,
    val custo: Int = 0,
    val almas: Int? = null,
    val vibra: Int = -1,
    val vibraPadrao: String = "",
) {
    companion object {
        fun de(me: JSONObject?): Rapido {
            if (me == null) return Rapido()
            val buzz = me.optJSONArray("buzz")
            return Rapido(
                cooldown = me.optDouble("cooldown", 0.0).toFloat(),
                stamina = me.optDouble("stamina", 1.0).toFloat(),
                cansado = me.optBoolean("tired"),
                municao = me.optInt("ammo"),
                pente = me.optInt("mag"),
                recarga = me.optDouble("reload", 0.0).toFloat(),
                energia = me.optInt("energy"),
                energiaMax = me.optInt("emax"),
                custo = me.optInt("ecost"),
                almas = me.inteiroOuNulo("souls"),
                vibra = buzz?.optInt(0, -1) ?: -1,
                vibraPadrao = buzz?.optString(1, "") ?: "",
            )
        }
    }
}

class Me(val o: JSONObject) {
    val vaga = o.optInt("slot")
    val dono = o.optBoolean("owner")
    val personagem = o.optInt("char")
    val arma = o.optInt("weapon")
    val pronto = o.optBoolean("ready")
    val time: Int? = o.inteiroOuNulo("team")
    val vibracaoNoJogo = o.optBoolean("vibracao", true)
    val escolha = o.optInt("choice")
    val jogando = o.optBoolean("playing")
    val melhorias: List<Melhoria> = o.optJSONArray("options").objetos().map { m ->
        val c = m.optJSONArray("color")
        val cor = if (c != null && c.length() >= 3)
            0xFF000000L or (c.optInt(0).toLong() shl 16) or (c.optInt(1).toLong() shl 8) or c.optInt(2).toLong()
        else 0xFFFFD75AL
        Melhoria(m.texto("name"), m.texto("desc"), cor)
    }
    val loja: Loja? = o.optJSONObject("shop")?.let { Loja(it) }
    val penalti: Penalti? = o.optJSONObject("penalty")?.let { Penalti(it.texto("role", "espera"), it.texto("hero")) }
    val mao: Mao? = o.optJSONObject("hand")?.let { Mao(it.texto("name"), it.texto("icon")) }

    /** O apelido que a TV está mostrando (null = P1, P2...). */
    val apelido: String? = o.textoOuNulo("nick")

    /** Pode mandar frase para a equipe agora (partida com time, ou campanha). */
    val podeChamar: Boolean = o.optBoolean("team_calls")

    /** As frases dos colegas de time ainda no ar (a mais nova por último). */
    val chamadas: List<Chamada> = o.optJSONArray("calls").objetos().map {
        Chamada(it.optInt("id"), it.optInt("from"), it.texto("label"), it.texto("kind"))
    }
    val rapido = Rapido.de(o)
}

class Status(val o: JSONObject) {
    val fase = o.texto("phase", "menu")
    val modo = o.texto("mode", "battle")
    val ativos: List<Int> = o.optJSONArray("active")?.let { a -> (0 until a.length()).map { a.optInt(it) } } ?: emptyList()
    val banner = o.texto("banner")
    val roster = o.optInt("roster")
    val hud = o.texto("hud", "battle")
    val novidades: List<String> = o.optJSONArray("news")?.let { a -> (0 until a.length()).map { a.optString(it) } } ?: emptyList()
    val paginaNovidade: PaginaNovidade? = o.optJSONObject("news_page")?.let {
        PaginaNovidade(it.optInt("index"), it.optInt("total"), it.texto("title"))
    }
    val vagas: Map<Int, VagaInfo> = buildMap {
        val s = o.optJSONObject("slots")
        if (s != null) for (k in s.keys()) {
            val v = s.optJSONObject(k) ?: continue
            val n = k.toIntOrNull() ?: continue
            put(n, VagaInfo(v.optBoolean("claimed"), v.optBoolean("connected")))
        }
    }
    val me: Me? = o.optJSONObject("me")?.let { Me(it) }

    /** Jogo da v1.60.0 em diante: apelido, reações, resumo da partida e MAPA. */
    val temExtras = o.has("map")

    /** A partida tem MAPA para o celular (fase da campanha ou Casa). */
    val temMapa = o.optBoolean("map")

    /** O resumo da partida que acabou (só na tela de resultado). */
    val resumo: Resumo? = o.optJSONObject("summary")?.let { try { Resumo(it) } catch (e: Exception) { null } }
}

/** A banca aberta no celular (loja, ferreiro, altar, cacos, armário) ou o computador da Casa. */
class Loja(val o: JSONObject) {
    val tipo = o.texto("kind")
    val titulo = o.texto("title")
    val saldo = o.optInt("souls")
    val unidade = o.texto("unit").ifEmpty { "ALMAS" }
    val marcado: String? = o.textoOuNulo("picked")
    val acao: String? = o.textoOuNulo("action")
    val tela = o.optBoolean("screen")
    val versao = o.optInt("version")
    val digitando = o.optBoolean("typing")
    val foco = o.texto("focus")
    val proporcao = o.optDouble("ratio", 1.9).toFloat().takeIf { it > 0.2f } ?: 1.9f
    val campos: List<Campo> = o.optJSONArray("fields")?.let { a ->
        (0 until a.length()).mapNotNull { i ->
            val f = a.optJSONArray(i) ?: return@mapNotNull null
            if (f.length() < 5) null
            else Campo(f.optDouble(0).toFloat(), f.optDouble(1).toFloat(), f.optDouble(2).toFloat(),
                f.optDouble(3).toFloat(), f.optString(4))
        }
    } ?: emptyList()
    val npc: Npc? = o.optJSONObject("npc")?.let { Npc(it.texto("name"), it.texto("label"), it.texto("fala")) }
    val colegas: List<Colega> = o.optJSONArray("mates").objetos().map {
        Colega(it.optInt("slot"), it.texto("label"), it.texto("name"), it.optInt("souls"))
    }
    val itens: List<Item> = o.optJSONArray("items").objetos().map { Item(it) }

    data class Campo(val x: Float, val y: Float, val w: Float, val h: Float, val nome: String)
    data class Npc(val nome: String, val rotulo: String, val fala: String)
    data class Colega(val vaga: Int, val rotulo: String, val nome: String, val almas: Int)
}

class Item(val o: JSONObject) {
    val id = o.texto("id")
    val rotulo = o.texto("label")
    val custo = o.optInt("cost")
    val desc = o.texto("desc")
    val ok = o.optBoolean("ok", true)
    val podePagar = o.optBoolean("afford", true)
    val cor = o.texto("color", "#f4ecd8")
    val info: JSONObject? = o.optJSONObject("info")
    val tipo: String = info?.texto("type") ?: ""
}

/** Uma arma como o jogo descreve para o celular (weapon_card do market.py). */
class CartaArma(val o: JSONObject) {
    val nome = o.texto("name")
    val icone = o.texto("icon")
    val raridade = o.texto("rarity")
    val cor = o.texto("color", "#8a86a0")
    val perto = o.optBoolean("melee")
    val nivel = o.optInt("level")
    val encanto: String? = o.textoOuNulo("enchant")
    val dano = o.optInt("damage")
    val pente = o.optInt("mag")
    val energia: Int? = o.inteiroOuNulo("energy")

    /** "GRÁTIS", "4 POR TIRO", "6 POR GOLPE" ou null (fora da campanha). */
    val textoEnergia: String?
        get() = when {
            energia == null -> null
            energia == 0 -> "GRÁTIS"
            else -> "$energia POR " + if (perto) "GOLPE" else "TIRO"
        }
}

/** Um personagem do elenco (/api/roster). */
class Heroi(val o: JSONObject) {
    val nome = o.texto("name")
    val vida = o.optDouble("hp", 100.0).toFloat()
    val velocidade = o.optDouble("speed", 3.0).toFloat()
    val habilidade = o.texto("ability")
    val habilidadeDesc = o.texto("ability_desc")
    val superFutebol = o.texto("soccer_power")
    val superFutebolDesc = o.texto("soccer_desc")
    val passivaFutebol = o.texto("soccer_passive")
    val passivaFutebolDesc = o.texto("soccer_passive_desc")
    val superBasquete = o.texto("basket_power")
    val superBasqueteDesc = o.texto("basket_desc")
    val passivaBasquete = o.texto("basket_passive")
    val armas: List<ArmaHeroi> = o.optJSONArray("weapons").objetos().map {
        ArmaHeroi(it.texto("name"), it.texto("icon"), it.optBoolean("melee"), it.optDouble("damage", 0.0).toFloat(),
            it.optInt("mag"), it.texto("note"))
    }
}

data class ArmaHeroi(val nome: String, val icone: String, val perto: Boolean, val dano: Float, val pente: Int, val nota: String)
