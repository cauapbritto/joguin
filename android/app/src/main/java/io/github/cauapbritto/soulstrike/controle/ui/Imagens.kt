package io.github.cauapbritto.soulstrike.controle.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.LruCache
import androidx.compose.runtime.Composable
import androidx.compose.runtime.produceState
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import io.github.cauapbritto.soulstrike.controle.rede.Http
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

/**
 * Desenhos que vêm do jogo (heróis, armas, skins, pets, quem atende na banca). Ficam guardados na
 * memória: a loja abre e fecha várias vezes e nada é baixado de novo.
 */
object Imagens {
    /** http://ip:porta do jogo conectado (o Canal muda ao conectar). */
    @Volatile
    var base: String = ""

    private val cache = object : LruCache<String, ImageBitmap>(24 * 1024 * 1024) {
        override fun sizeOf(key: String, value: ImageBitmap): Int = value.width * value.height * 4
    }

    fun url(caminho: String): String = if (caminho.startsWith("http")) caminho else base + caminho

    fun naMemoria(caminho: String): ImageBitmap? = cache.get(url(caminho))

    suspend fun carregar(caminho: String): ImageBitmap? = withContext(Dispatchers.IO) {
        val u = url(caminho)
        cache.get(u) ?: run {
            val r = Http.get(u, 4000)
            if (r == null || !r.ok || r.corpo.isEmpty()) {
                null
            } else {
                val opcoes = BitmapFactory.Options().apply {
                    inScaled = false
                    inPreferredConfig = Bitmap.Config.ARGB_8888
                }
                val bmp = try {
                    BitmapFactory.decodeByteArray(r.corpo, 0, r.corpo.size, opcoes)
                } catch (e: Exception) {
                    null
                }
                bmp?.asImageBitmap()?.also { cache.put(u, it) }
            }
        }
    }
}

/** Um desenho do jogo (null enquanto chega). Tenta de novo algumas vezes se a rede engasgar. */
@Composable
fun imagemDoJogo(caminho: String?): ImageBitmap? {
    val estado = produceState(initialValue = caminho?.let { Imagens.naMemoria(it) }, caminho) {
        if (caminho == null) {
            value = null
            return@produceState
        }
        val pronta = Imagens.naMemoria(caminho)
        if (pronta != null) {
            value = pronta
            return@produceState
        }
        for (tentativa in 1..4) {
            val img = Imagens.carregar(caminho)
            if (img != null) {
                value = img
                return@produceState
            }
            delay(1200L * tentativa)
        }
    }
    return estado.value
}
