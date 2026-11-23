package io.github.cauapbritto.soulstrike.controle.telas

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import io.github.cauapbritto.soulstrike.controle.ui.Texto

/** As telas de quando já está no jogo (controle, espera, seleção, loja...). */
@Composable
fun TelaJogo() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Texto("CONECTADO", tam = 16)
    }
}
