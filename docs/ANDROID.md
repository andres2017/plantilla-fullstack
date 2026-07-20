# Android (Capacitor) — Guía de empaquetado

Este proyecto se compila a web (React/CRA) y, con [Capacitor](https://capacitorjs.com/),
a un proyecto nativo Android (`frontend/android`) sin duplicar código: el WebView de
la app carga el mismo build de producción del frontend. La generación de builds está
automatizada por el subagente `android-release` (`.claude/agents/android-release.md`).

## Flujo de build

```bash
cd frontend
yarn build          # build web de React
npx cap sync android # copia el build + plugins nativos a frontend/android
cd android
./gradlew assembleDebug    # APK de prueba (sin firma de release)
./gradlew bundleRelease    # AAB de release (requiere keystore, ver abajo)
```

`yarn build:mobile` (definido en `frontend/package.json`) hace los dos primeros pasos
en un solo comando.

Requisitos locales para compilar: **JDK 21** (el módulo `@capacitor/android` fija
`sourceCompatibility`/`targetCompatibility` en `JavaVersion.VERSION_21` — JDK 17 no
alcanza y falla con `error: invalid source release: 21`) y Android SDK
(`ANDROID_HOME` apuntando a `platform-tools`, `build-tools;34.0.0` y
`platforms;android-34` como mínimo). No hace falta Android Studio instalado — el
SDK cmdline-tools alcanza.

## Bautizar el proyecto en Android (además de los "3 pasos" del README)

`capacitor.config.json` y `frontend/android/app/build.gradle` traen el placeholder
`com.example.miapp` (`appId`/`applicationId` y `namespace`). Cambialo por tu dominio
real invertido (ej. `com.tuempresa.tuapp`) **antes del primer release** — el
`applicationId` es inmutable una vez publicado en Google Play. Hay que actualizarlo
en los dos archivos (Capacitor no los sincroniza automáticamente entre sí).

## Generar el keystore de release

**El keystore de firma es la pieza más sensible del proyecto.** Si se pierde, Google
Play rechaza para siempre cualquier actualización futura de la app (hay que publicarla
como app nueva, perdiendo reseñas e instalaciones). Si se filtra, cualquiera puede
firmar y distribuir una versión maliciosa que Android trata como "la app legítima".
A diferencia de un `JWT_SECRET`, **no se puede rotar**.

1. Generarlo (una sola vez, con `keytool`, que viene con el JDK):

   ```bash
   keytool -genkeypair -v \
     -keystore miapp-release.jks \
     -alias miapp \
     -keyalg RSA -keysize 2048 -validity 10000
   ```

   Te pedirá una contraseña del keystore y una contraseña de la clave (pueden ser
   iguales) y datos de identidad (organización, ciudad, país) — se incrustan en el
   certificado, no son secretos, pero sé consistente porque Google Play los muestra.

2. Crear `frontend/android/keystore.properties` (NUNCA `frontend/android/app/`, y
   NUNCA lo agregues con `git add -f`; `.gitignore` ya lo bloquea):

   ```properties
   storeFile=C:/ruta/segura/fuera/del/repo/miapp-release.jks
   storePassword=la-contraseña-del-keystore
   keyAlias=miapp
   keyPassword=la-contraseña-de-la-clave
   ```

   `frontend/android/app/build.gradle` ya está preparado para leer este archivo
   automáticamente si existe (bloque `signingConfigs.release`); si no existe, los
   builds de debug siguen funcionando igual y `bundleRelease` simplemente sale sin
   firmar.

3. **Guarda el `.jks` y las contraseñas fuera del repositorio**, en al menos dos
   lugares independientes:
   - Un gestor de contraseñas del equipo (1Password, Bitwarden, etc.) — sube el
     archivo `.jks` como adjunto binario, no solo las contraseñas.
   - Un backup cifrado separado (USB/disco externo, o un bucket privado con
     cifrado en reposo) que no dependa de la misma cuenta que el gestor de
     contraseñas, para no tener un único punto de falla.

   Nunca lo subas a un chat, un issue, un Google Doc sin cifrar, ni a ningún
   servicio que no sea explícitamente para secretos.

4. Verifica antes de cada release que el keystore nunca quedó trackeado:

   ```bash
   git ls-files | grep -E '\.(jks|keystore)$'
   ```

   Si aparece algo, ese keystore debe tratarse como comprometido — hay que evaluar
   generar uno nuevo (con el costo de romper la cadena de actualizaciones en Play
   Store) y limpiar el historial de git.

## Checklist antes de publicar en Google Play

- [ ] **Ícono adaptativo**: reemplazar los `mipmap-*/ic_launcher*` generados por
      Capacitor (son un placeholder) por el ícono real de la app en
      `frontend/android/app/src/main/res/mipmap-*`. Usar
      [Image Asset Studio](https://developer.android.com/studio/write/image-asset-studio)
      o `npx @capacitor/assets generate` con un ícono fuente de 1024x1024.
- [ ] **Splash screen**: instalar y configurar `@capacitor/splash-screen` si se
      quiere una pantalla de carga con marca propia (hoy la app arranca con el
      splash por defecto de Capacitor).
- [ ] **Nombre y `applicationId`**: cambiar el placeholder `com.example.miapp` (ver
      sección "Bautizar el proyecto" arriba) — es inmutable una vez publicado.
- [ ] **Permisos**: `frontend/android/app/src/main/AndroidManifest.xml` hoy solo
      declara `INTERNET`. Si se agregan plugins de Capacitor que requieran cámara,
      ubicación, notificaciones, etc., cada permiso nuevo debe justificarse en la
      ficha de Play Console (Google audita permisos sensibles).
- [ ] **`versionCode`/`versionName`**: `versionCode` debe subir en cada release
      (entero, nunca repetir ni bajar); `versionName` es el string visible al
      usuario (semver). Los gestiona el subagente `android-release` como parte de
      su flujo estricto.
- [ ] **`targetSdkVersion`**: Google Play exige un `targetSdkVersion` reciente
      (revisar el mínimo vigente en la consola de Play antes de cada release; hoy
      el proyecto usa la versión definida en `frontend/android/variables.gradle`).
- [ ] **Firma**: AAB firmado con el keystore de release (ver arriba), nunca con el
      keystore de debug.
- [ ] **URL del backend**: la app empaquetada usa la `REACT_APP_BACKEND_URL`
      horneada en build-time (`frontend/.env` o variable de entorno del build) —
      confirmar que apunta al backend de producción, no a `localhost`, antes de
      generar el release.
- [ ] **Cookies cross-origin**: el WebView de Capacitor sirve la app desde un
      origen propio (`https://localhost` por defecto), distinto del dominio del
      backend. Igual que con cualquier deploy donde frontend y backend quedan en
      dominios distintos, hay que fijar `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true`
      en el backend, y anclar `CORS_ORIGIN_REGEX`/`CORS_ORIGINS` al origen real
      (ver `backend/.env.example`) — nunca dejar el backend con los defaults de
      desarrollo local en producción.
- [ ] **Política de privacidad y ficha de la Play Console**: URL de política de
      privacidad, clasificación de contenido, y formulario de seguridad de datos
      (Data Safety) — requisitos de Google, no del código.

## Notas

- El artefacto que genera el subagente `android-release` por defecto es un
  **APK debug** (evidencia rápida de que el build nativo compila, firmado
  automáticamente con el keystore de debug del SDK). El **AAB de release**
  firmado es un paso explícito y separado que requiere el keystore real.
- `frontend/android` es un proyecto Gradle generado por `npx cap add android`;
  no edites a mano archivos que Capacitor regenera en cada `cap sync`
  (`app/src/main/assets/public`, `capacitor.config.json` copiado, etc.) — los
  cambios se perderían en el siguiente sync.
