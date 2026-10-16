@ECHO OFF
SETLOCAL
SET APP_HOME=%~dp0
IF EXIST "%APP_HOME%gradle\wrapper\gradle-wrapper.jar" GOTO run
WHERE gradle >NUL 2>NUL
IF NOT ERRORLEVEL 1 GOTO system_gradle
ECHO Gradle Wrapper JAR is missing and no system Gradle was found.
ECHO Install Gradle 8.7+ or run scripts\bootstrap-android.ps1 from the repository root.
EXIT /B 1
:run
SET CLASSPATH=%APP_HOME%gradle\wrapper\gradle-wrapper.jar
IF DEFINED JAVA_HOME ("%JAVA_HOME%\bin\java.exe" -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*) ELSE (java -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*)
GOTO done
:system_gradle
gradle %*
:done
ENDLOCAL
