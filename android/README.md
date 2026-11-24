# Soul Strike Controle (app Android)

O controle do Soul Strike num app de verdade para Android 8.0 ou mais novo. Faz tudo o que a
página do celular faz (escolha de personagem, partida, lojas, pênaltis, computador da Casa...),
com resposta mais rápida, vibração com vários níveis e a câmera para ler o QR Code da TV.
A página do celular continua funcionando para quem não tem Android.

## Baixar e instalar

1. No celular, baixe o `SoulStrikeControle.apk` da última Release:
   <https://github.com/cauapbritto/joguin/releases/latest/download/SoulStrikeControle.apk>
2. Abra o arquivo. Na primeira vez o Android pede para permitir "instalar apps desconhecidos"
   para o navegador (ou para o app de arquivos): permita e toque em **Instalar**.
3. Para atualizar: quando o jogo é mais novo que o app, aparece **ATUALIZAR** na tela de espera
   (e em **AJUSTES DO APP > PROCURAR VERSÃO NOVA**). O app baixa o APK da Release e o Android
   instala por cima; na primeira vez ele pede a licença "permitir desta fonte" para o app.
   Os ajustes e o controle salvo ficam.

## Conectar no jogo

O celular e o computador precisam estar na mesma rede Wi-Fi. No menu do app tem três jeitos:

- **LER QR CODE**: abre a câmera e lê o QR Code da tela "Conecte os celulares" (o mesmo do site).
- **PROCURAR NA REDE**: o app chama na rede e o jogo responde sozinho, com o nome do computador.
- **DIGITAR ENDEREÇO**: teclado de números para o endereço que aparece na TV (`192.168.0.10:5000`).

Depois é só escolher a vaga (P1 a P4). Se o Wi-Fi cair, o app avisa (e vibra) e fica tentando
voltar sozinho.

Se o computador tiver firewall ligado, libere a porta 5000 em **TCP e UDP**
(`sudo ufw allow 5000` no Linux; o `INSTALAR.sh` já oferece isso). O app usa o TCP como o site
e o UDP para o canal rápido.

Permissões que o app pede: **câmera** (só para ler o QR Code) e, nos Android mais novos,
**dispositivos na rede local** (para achar e falar com o jogo). A vibração não pede nada.

## O que tem no app

- Controle de cada modo com analógico e botões em arco no polegar direito, como no site:
  duelo, campanha, futebol, basquete e pênaltis, com anéis de recarga, fôlego e munição.
- **AJUSTES** do controle: tamanho, transparência, analógico solto, fixo ou **INCLINAR** (anda
  inclinando o celular; tocar na metade esquerda zera), modo canhoto,
  arrastar os botões, clique ao tocar e o nível da vibração (desligada, fraca, média, forte).
  Fica salvo separado para cada modo.
- Botão de **PAUSA** e o menu da pausa no próprio celular.
- Lojas, ferreiro, altar, armários e loja de CACOS com o vendedor, doação de almas, cupons e o
  computador da Casa (a tela dele aparece no celular e o toque vira clique na TV).
- Telas de espera, novidades (PLANTÃO), resultados e história com os botões para avançar.
- **Apelido na TV** (até 10 letras, no lugar de P1) e **reações rápidas** (GG, KKKK, VEM!,
  PALMAS) num balão em cima do boneco, com somzinho.
- Botão **EQUIPE** (futebol, basquete e campanha): frases prontas como PASSA! e AJUDA! que só os
  colegas de time recebem, com vibração, e que aparecem num balão na cor do time na TV.
- **Resumo da partida** no celular (placar, seus números e o destaque) e, na campanha e na Casa,
  o **MAPA** com o **CADERNO DE SEGREDOS** sem pausar a TV.
- Segurar o ícone do app mostra **VOLTAR AO JOGO** (o último computador, na mesma vaga).

## Compilar

### No GitHub (automático)

A Action **App Android (APK)** (`.github/workflows/android.yml`) compila o APK em todo push e
PR que mexe em `android/`. O arquivo fica nos artefatos da execução (`soulstrike-controle-apk`).
Nas tags `v*` ele também vai anexado na Release da versão, ao lado do `.deb`.

### No Android Studio

1. Abra a pasta `android/` (não a raiz do repositório) no Android Studio.
2. Use o JDK 17 ou mais novo (o que vem com o Android Studio serve).
3. Deixe o Gradle sincronizar e rode no celular (▶) ou gere o APK em
   **Build > Generate App Bundles or APKs > Generate APKs**.

Pela linha de comando:

```bash
cd android
./gradlew assembleRelease
# APK em app/build/outputs/apk/release/app-release.apk
```

A versão do app é a mesma do jogo: o Gradle lê o `__version__` de `soulstrike/__init__.py`.

### Assinatura

A chave `app/controle.jks` e a senha dela (no `app/build.gradle.kts`) ficam no repositório
**de propósito**: assim o APK do GitHub e o compilado no Android Studio têm a mesma assinatura e
um instala por cima do outro sem perder os ajustes. Ela serve só para isso; para publicar numa
loja de apps, seria preciso uma chave nova e guardada em segredo.

## Como o app fala com o jogo

- **HTTP na porta 5000** (o mesmo servidor do site): `/api/app` (é um Soul Strike? que versão?),
  `/api/join` e `/api/leave` (vaga), `/api/status`, `/api/shop`, `/api/news` e `/api/tela.png`.
- **UDP na porta 5000** (`soulstrike/net/rapido.py`): o app manda o estado dos botões várias vezes
  por segundo e o jogo responde com um pulso curto (fase, HUD, recargas, munição, energia e as
  vibrações), então o dedo e a vibração chegam sem esperar o HTTP. Se o UDP não passar, o app usa
  só o HTTP, como o site.
- O código fica em `app/src/main/java/io/github/cauapbritto/soulstrike/controle/`:
  `rede/` (conexão, descoberta e canal), `jogo/` (status e entrada), `telas/` (cada tela),
  `ui/` (tema, fonte, botões e imagens do jogo) e `vibra/` (padrões de vibração).
