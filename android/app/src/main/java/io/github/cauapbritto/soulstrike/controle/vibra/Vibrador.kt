package io.github.cauapbritto.soulstrike.controle.vibra

import android.content.Context
import android.media.AudioAttributes
import android.os.Build
import android.os.SystemClock
import android.os.VibrationAttributes
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import kotlin.math.roundToInt

/**
 * Vibração do controle. Nos celulares com motor bom (Android 11+), cada evento do jogo vira uma
 * composição de "primitivas" (clique, baque, giro, subida...): um golpe é um clique seco, o gol é
 * uma subida com dois cliques, a queda é um baque que morre. Nos outros, uma onda com força variável
 * e, no último caso, só liga/desliga. A força (DESL, FRACA, MÉDIA, FORTE) escala tudo.
 */
class Vibrador(context: Context, private val nivel: () -> Int) {
    private val motor: Vibrator? = if (Build.VERSION.SDK_INT >= 31) {
        (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
    } else {
        @Suppress("DEPRECATION")
        context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    }

    /** O celular tem motor de vibração. */
    val existe: Boolean = motor?.hasVibrator() == true
    private val forca: Boolean = motor?.hasAmplitudeControl() == true
    private val prim11: Boolean = primitivas11(motor)
    private val prim12: Boolean = prim11 && primitivas12(motor)

    /** Que tipo de vibração este celular faz (aparece nos ajustes). */
    val qualidade: String
        get() = when {
            !existe -> "SEM MOTOR"
            prim12 || prim11 -> "MOTOR HÁPTICO"
            forca -> "COM FORÇA"
            else -> "SIMPLES"
        }

    private var ultimoToque = 0L

    /** Vibra um padrão do jogo (hit, big_hit, score, super, call, tick, go, block, fall) ou do app. */
    fun tocar(nome: String) {
        val v = motor ?: return
        if (!existe) return
        val n = nivel()
        if (n <= 0) return
        if (nome == "toque") {                       // clique de botão: no máximo um a cada 35 ms
            val agora = SystemClock.uptimeMillis()
            if (agora - ultimoToque < 35) return
            ultimoToque = agora
        }
        val p = PADROES[nome] ?: return
        val escala = ESCALAS[n.coerceIn(0, 3)]
        val efeito = try {
            when {
                prim12 && p.forte != null -> compor(p.forte, escala)
                prim11 && p.simples != null -> compor(p.simples, escala)
                else -> onda(p, escala, n)
            }
        } catch (e: Exception) {
            null
        } ?: return
        try {
            if (Build.VERSION.SDK_INT >= 33) {
                v.vibrate(efeito, VibrationAttributes.createForUsage(VibrationAttributes.USAGE_MEDIA))
            } else {
                @Suppress("DEPRECATION")
                v.vibrate(efeito, AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME).build())
            }
        } catch (e: Exception) {
            // sem vibração não é motivo para travar o controle
        }
    }

    private fun compor(lista: List<Prim>, escala: Float): VibrationEffect? {
        if (Build.VERSION.SDK_INT < 30) return null
        val c = VibrationEffect.startComposition()
        for (pr in lista) c.addPrimitive(pr.id, (pr.escala * escala).coerceIn(0.05f, 1f), pr.atraso)
        return c.compose()
    }

    private fun onda(p: Padrao, escala: Float, n: Int): VibrationEffect {
        // sem controle de força, a FRACA fica mais curta (é o que dá para mudar)
        val curto = if (forca) 1f else when (n) { 1 -> 0.55f; 2 -> 0.8f; else -> 1f }
        val tempos = LongArray(p.tempos.size) { i ->
            if (i % 2 == 1) (p.tempos[i] * curto).toLong().coerceAtLeast(6) else p.tempos[i]
        }
        val forcas = IntArray(p.forcas.size) { i ->
            if (p.forcas[i] == 0) 0 else (p.forcas[i] * escala).roundToInt().coerceIn(1, 255)
        }
        return VibrationEffect.createWaveform(tempos, forcas, -1)
    }

    private class Prim(val id: Int, val escala: Float, val atraso: Int = 0)

    /** ``forte``: com baque/giro (Android 12+); ``simples``: só clique/tique/subida (Android 11). */
    private class Padrao(val forte: List<Prim>?, val simples: List<Prim>?, val tempos: LongArray, val forcas: IntArray)

    private companion object {
        val ESCALAS = floatArrayOf(0f, 0.45f, 0.72f, 1f)

        // números das primitivas do Android (VibrationEffect.Composition)
        const val CLICK = 1
        const val THUD = 2
        const val SPIN = 3
        const val QUICK_RISE = 4
        const val SLOW_RISE = 5
        const val QUICK_FALL = 6
        const val TICK = 7
        const val LOW_TICK = 8

        fun primitivas11(v: Vibrator?): Boolean {
            if (v == null || Build.VERSION.SDK_INT < 30) return false
            return try {
                v.areAllPrimitivesSupported(CLICK, TICK, QUICK_RISE, SLOW_RISE, QUICK_FALL)
            } catch (e: Exception) {
                false
            }
        }

        fun primitivas12(v: Vibrator?): Boolean {
            if (v == null || Build.VERSION.SDK_INT < 31) return false
            return try {
                v.areAllPrimitivesSupported(THUD, SPIN, LOW_TICK)
            } catch (e: Exception) {
                false
            }
        }

        fun p(vararg x: Prim) = x.toList()

        val PADROES: Map<String, Padrao> = mapOf(
            // ── eventos do jogo (o mesmo nome que o jogo manda) ──
            "hit" to Padrao(p(Prim(CLICK, 0.85f)), p(Prim(CLICK, 0.85f)),
                longArrayOf(0, 30), intArrayOf(0, 200)),
            "big_hit" to Padrao(p(Prim(THUD, 1f), Prim(CLICK, 0.7f, 30)), p(Prim(CLICK, 1f), Prim(QUICK_FALL, 0.9f, 10)),
                longArrayOf(0, 70), intArrayOf(0, 255)),
            "score" to Padrao(p(Prim(QUICK_RISE, 0.7f), Prim(CLICK, 1f, 40), Prim(CLICK, 1f, 70), Prim(SPIN, 0.5f, 60)),
                p(Prim(QUICK_RISE, 0.7f), Prim(CLICK, 1f, 40), Prim(CLICK, 1f, 70)),
                longArrayOf(0, 80, 40, 80), intArrayOf(0, 255, 0, 255)),
            "super" to Padrao(p(Prim(SPIN, 0.9f), Prim(CLICK, 0.6f, 20)), p(Prim(QUICK_RISE, 1f), Prim(CLICK, 0.6f, 10)),
                longArrayOf(0, 20, 20, 40), intArrayOf(0, 120, 0, 255)),
            "call" to Padrao(p(Prim(CLICK, 0.8f), Prim(CLICK, 0.8f, 110), Prim(CLICK, 0.8f, 110)),
                p(Prim(CLICK, 0.8f), Prim(CLICK, 0.8f, 110), Prim(CLICK, 0.8f, 110)),
                longArrayOf(0, 60, 80, 60, 80, 60), intArrayOf(0, 220, 0, 220, 0, 220)),
            "tick" to Padrao(p(Prim(TICK, 0.8f)), p(Prim(TICK, 0.8f)),
                longArrayOf(0, 15), intArrayOf(0, 110)),
            "go" to Padrao(p(Prim(SLOW_RISE, 0.7f), Prim(CLICK, 1f, 10)), p(Prim(SLOW_RISE, 0.7f), Prim(CLICK, 1f, 10)),
                longArrayOf(0, 140), intArrayOf(0, 255)),
            "block" to Padrao(p(Prim(LOW_TICK, 1f)), p(Prim(TICK, 0.5f)),
                longArrayOf(0, 12), intArrayOf(0, 90)),
            "fall" to Padrao(p(Prim(THUD, 1f), Prim(QUICK_FALL, 0.7f, 20), Prim(LOW_TICK, 1f, 60)),
                p(Prim(CLICK, 1f), Prim(QUICK_FALL, 0.8f, 20)),
                longArrayOf(0, 90, 30, 40), intArrayOf(0, 255, 0, 140)),
            // ── do próprio app ──
            "toque" to Padrao(p(Prim(TICK, 0.6f)), p(Prim(TICK, 0.6f)),
                longArrayOf(0, 10), intArrayOf(0, 70)),
            "correr" to Padrao(p(Prim(QUICK_RISE, 0.45f)), p(Prim(QUICK_RISE, 0.45f)),
                longArrayOf(0, 18), intArrayOf(0, 100)),
            "compra" to Padrao(p(Prim(CLICK, 0.6f), Prim(TICK, 1f, 50)), p(Prim(CLICK, 0.6f), Prim(TICK, 1f, 50)),
                longArrayOf(0, 10, 40, 20), intArrayOf(0, 150, 0, 220)),
            "leu" to Padrao(p(Prim(CLICK, 1f), Prim(CLICK, 1f, 90)), p(Prim(CLICK, 1f), Prim(CLICK, 1f, 90)),
                longArrayOf(0, 25, 70, 25), intArrayOf(0, 255, 0, 255)),
            "erro" to Padrao(p(Prim(THUD, 0.8f), Prim(THUD, 0.8f, 80)), p(Prim(CLICK, 1f), Prim(CLICK, 1f, 80)),
                longArrayOf(0, 40, 60, 40), intArrayOf(0, 200, 0, 200)),
            "caiu" to Padrao(p(Prim(THUD, 1f), Prim(THUD, 1f, 120)), p(Prim(CLICK, 1f), Prim(CLICK, 1f, 120)),
                longArrayOf(0, 60, 100, 60), intArrayOf(0, 255, 0, 255)),
            "teste" to Padrao(p(Prim(SLOW_RISE, 0.8f), Prim(QUICK_FALL, 0.8f), Prim(CLICK, 1f, 80), Prim(THUD, 0.9f, 80)),
                p(Prim(SLOW_RISE, 0.8f), Prim(QUICK_FALL, 0.8f), Prim(CLICK, 1f, 80)),
                longArrayOf(0, 200, 100, 200), intArrayOf(0, 255, 0, 255)),
        )
    }
}
