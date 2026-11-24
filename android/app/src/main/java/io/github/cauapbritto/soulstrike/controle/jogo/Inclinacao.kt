package io.github.cauapbritto.soulstrike.controle.jogo

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.view.Surface
import kotlin.math.hypot

/**
 * INCLINAR (AJUSTES DO CONTROLE > ANALÓGICO): o celular vira o analógico. Lê a gravidade (ou o
 * acelerômetro, alisado), gira conforme o lado em que o celular está deitado e conta a partir de
 * como o jogador segurava quando começou (ou quando tocou em ZERAR).
 *
 * ``aoMover(x, y, forte)``: x e y de -1 a 1 (direita e para baixo positivos), ``forte`` = inclinou
 * muito (corre no futebol e no basquete).
 */
class Inclinacao(
    context: Context,
    /** Surface.ROTATION_* da tela agora (o celular pode virar de lado no meio do jogo). */
    private val rotacao: () -> Int,
    private val aoMover: (Float, Float, Boolean) -> Unit,
) : SensorEventListener {
    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as? SensorManager
    private val sensor: Sensor? = sm?.getDefaultSensor(Sensor.TYPE_GRAVITY) ?: sm?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private val alisar = sensor?.type == Sensor.TYPE_ACCELEROMETER

    private var gx = 0f
    private var gy = 0f
    private var primeira = true
    private var zeroX = 0f
    private var zeroY = 0f
    private var zerar = true

    val existe: Boolean get() = sensor != null

    fun ligar(): Boolean {
        val s = sensor ?: return false
        primeira = true
        zerar = true
        return try {
            sm?.registerListener(this, s, SensorManager.SENSOR_DELAY_GAME) == true
        } catch (e: Exception) {
            false
        }
    }

    fun desligar() {
        try {
            sm?.unregisterListener(this)
        } catch (e: Exception) {
            // nada
        }
    }

    /** O jeito que o celular está agora vira o "parado". */
    fun zerar() {
        zerar = true
    }

    override fun onSensorChanged(ev: SensorEvent) {
        val ax = ev.values[0]
        val ay = ev.values[1]
        if (alisar && !primeira) {
            gx += (ax - gx) * 0.2f
            gy += (ay - gy) * 0.2f
        } else {
            gx = ax
            gy = ay
        }
        primeira = false
        // os eixos do sensor girados para o lado em que a tela está (o sinal acerta no dx/dy abaixo)
        val (rx, ry) = when (rotacao()) {
            Surface.ROTATION_90 -> -gy to gx
            Surface.ROTATION_270 -> gy to -gx
            Surface.ROTATION_180 -> -gx to -gy
            else -> gx to gy
        }
        if (zerar) {
            zeroX = rx
            zeroY = ry
            zerar = false
        }
        var dx = -(rx - zeroX) / GRAUS
        var dy = (ry - zeroY) / GRAUS
        val d = hypot(dx, dy)
        val forte = d > FORTE
        if (d < MORTA) {
            dx = 0f
            dy = 0f
        } else {
            val f = ((d - MORTA) / (1f - MORTA)).coerceAtMost(1f) / d
            dx *= f
            dy *= f
        }
        aoMover(dx, dy, forte)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private companion object {
        /** quanto de gravidade (m/s²) é inclinar até o fim (~25 graus) */
        const val GRAUS = 4.2f
        const val MORTA = 0.15f
        const val FORTE = 1.35f
    }
}
