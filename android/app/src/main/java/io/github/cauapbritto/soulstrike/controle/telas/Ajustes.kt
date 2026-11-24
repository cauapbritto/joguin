package io.github.cauapbritto.soulstrike.controle.telas

import android.os.Build
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import io.github.cauapbritto.soulstrike.controle.AppEstado
import io.github.cauapbritto.soulstrike.controle.BuildConfig
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.Tela
import io.github.cauapbritto.soulstrike.controle.atualizar.Atualizador
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.u

val NIVEIS_VIBRACAO = listOf("DESL.", "FRACA", "MÉDIA", "FORTE")

/** O que o TESTAR VIBRAÇÃO responde (e por que não vibrou, quando não vibra). */
fun testarVibracao(app: AppEstado, vibracaoNoJogo: Boolean?): String {
    val v = app.vibrador
    return when {
        !v.existe -> "ESTE CELULAR NÃO TEM MOTOR DE VIBRAÇÃO"
        app.vibracao <= 0 -> "A VIBRAÇÃO ESTÁ DESLIGADA AQUI: ESCOLHA FRACA, MÉDIA OU FORTE"
        else -> {
            v.tocar("teste")
            val nome = NIVEIS_VIBRACAO[app.vibracao]
            if (vibracaoNoJogo == false) "BZZ! ASSIM É A $nome. NO JOGO, A VIBRAÇÃO ESTÁ DESLIGADA NAS OPÇÕES"
            else "BZZ! ASSIM É A $nome. NÃO VIBROU? VEJA A VIBRAÇÃO DE MÍDIA NOS AJUSTES DO ANDROID"
        }
    }
}

/** DESL. FRACA MÉDIA FORTE (a escolhida em dourado). */
@Composable
fun SeletorVibracao(modifier: Modifier = Modifier, aoMudar: (Int) -> Unit = {}) {
    val app = LocalApp.current
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(8.u)) {
        NIVEIS_VIBRACAO.forEachIndexed { i, nome ->
            Botao(
                nome, Modifier.weight(1f), altura = 32,
                tipo = if (app.vibracao == i) TipoBotao.DOURADO else TipoBotao.NORMAL,
            ) {
                app.mudarVibracao(i)
                if (i > 0) app.vibrador.tocar("teste")
                aoMudar(i)
            }
        }
    }
}

/** AJUSTES DO APP (a engrenagem do menu): vibração, clique, rede local e os jogos guardados. */
@Composable
fun TelaAjustesApp() {
    val app = LocalApp.current
    var recado by remember { mutableStateOf("") }
    var recentes by remember { mutableIntStateOf(app.prefs.recentes().size) }
    var editarApelido by remember { mutableStateOf(false) }
    val at = app.atualizador
    Box(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize()) {
            Cabecalho {
                Botao("VOLTAR", icone = R.drawable.ic_voltar, altura = 32) { app.tela = Tela.MENU }
                Texto("AJUSTES DO APP", tam = 16, sombra = true, linhas = 1)
            }
            Column(
                Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.u, vertical = 16.u),
                verticalArrangement = Arrangement.spacedBy(16.u),
            ) {
                Secao("APELIDO NA TV", "A TV MOSTRA NO LUGAR DE P1 (NO LOBBY, NA ESCOLHA E EM CIMA DO BONECO)") {
                    LinhaApelido(0) { editarApelido = true }
                }
                Secao("ATUALIZAÇÃO", "ESTE APP: v${at.versaoApp}. O APP BAIXA O NOVO DO GITHUB E INSTALA POR CIMA") {
                    val achou = at.noGithub
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.u)) {
                        Botao(
                            if (at.fase == Atualizador.Fase.PROCURANDO) "PROCURANDO..." else "PROCURAR VERSÃO NOVA",
                            altura = 32, ativo = !at.ocupado,
                        ) { at.procurar() }
                        if (achou != null && !at.maisNova(achou)) Texto("NO GITHUB: v$achou", cor = Cores.Muted, linhas = 1)
                    }
                    if (at.recado.isNotEmpty() && at.fase != Atualizador.Fase.ERRO) Texto(at.recado, cor = Cores.Brass)
                    FaixaAtualizar(achou)
                }
                Secao("VIBRAÇÃO", "MOTOR DESTE CELULAR: ${app.vibrador.qualidade}") {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.u)) {
                        SeletorVibracao(Modifier.weight(1f)) { recado = "" }
                        Botao("TESTAR", icone = R.drawable.i_vibrar, altura = 32) {
                            recado = testarVibracao(app, app.canal.status?.me?.vibracaoNoJogo)
                        }
                    }
                    if (recado.isNotEmpty()) Texto(recado, cor = Cores.Brass)
                }
                Secao("CLIQUE AO TOCAR", "UM TIQUINHO DE VIBRAÇÃO A CADA BOTÃO APERTADO") {
                    Botao(
                        if (app.clique) "LIGADO" else "DESLIGADO", altura = 32, ligado = app.clique,
                    ) { app.mudarClique(!app.clique) }
                }
                if (Build.VERSION.SDK_INT >= 37) {
                    Secao("REDE LOCAL", "O ANDROID 17 PEDE LICENÇA PARA FALAR COM O COMPUTADOR DO JOGO") {
                        if (app.redeLocalNegada) {
                            Botao("PERMITIR", tipo = TipoBotao.VERDE, altura = 32) {
                                app.pedirRedeLocal?.invoke()
                            }
                        } else {
                            Texto("PERMITIDA", cor = Cores.Moss)
                        }
                    }
                }
                Secao("JOGOS GUARDADOS", "O VOLTAR AO... DO MENU E OS RECENTES DE DIGITAR") {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.u)) {
                        Texto(if (recentes == 1) "1 JOGO" else "$recentes JOGOS", cor = Cores.Bone)
                        Botao("ESQUECER", altura = 32, ativo = recentes > 0) {
                            app.prefs.esquecerRecentes()
                            recentes = 0
                        }
                    }
                }
                Secao("SOBRE", "SOUL STRIKE CONTROLE v${BuildConfig.VERSION_NAME}") {
                    Texto(
                        "O CONTROLE MANDA OS BOTÕES PELO CANAL RÁPIDO (UDP NA PORTA 5000) E, SE ELE NÃO PASSAR, " +
                            "PELO MESMO CAMINHO DO SITE. A VAGA FICA GUARDADA 20 S SE A WI-FI CAIR.",
                        cor = Cores.Muted,
                    )
                }
            }
        }
        if (editarApelido) EditarApelido(aoFechar = { editarApelido = false })
    }
}

@Composable
private fun Secao(titulo: String, sub: String, conteudo: @Composable () -> Unit) {
    val m = LocalMedidas.current
    Column(
        Modifier
            .fillMaxWidth()
            .moldura(m, fundo = Cores.Ink3)
            .padding(12.u),
        verticalArrangement = Arrangement.spacedBy(8.u),
    ) {
        Texto(titulo, tam = 16, cor = Cores.Brass, sombra = true)
        Texto(sub, cor = Cores.Muted)
        conteudo()
    }
}
