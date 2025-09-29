from machine import Pin, ADC, Timer
import time

# Configuración de pines
ecg_sensor = ADC(Pin(34))
ecg_sensor.atten(ADC.ATTN_11DB)
ecg_sensor.width(ADC.WIDTH_12BIT)
led = Pin(2, Pin.OUT)

# Variables del sistema
frecuencia_muestreo = 100  # Hz por defecto
muestras = []
datos_crudos = []
datos_promedio = []
datos_mediana = []
datos_exponencial = []

# Configuración de filtros
filtros_activos = {
    'CRUDO': True,
    'PROMEDIO': True, 
    'MEDIANA': True,
    'EXPONENCIAL': True
}

# Timer para muestreo preciso
timer_muestreo = Timer(0)

# Función de diagnóstico del sensor
def diagnostico_sensor():
    print("\n=== DIAGNÓSTICO DEL SENSOR ===")
    print("Realizando 10 lecturas...")
    
    valores = []
    for i in range(10):
        valor = ecg_sensor.read()
        valores.append(valor)
        print(f"Lectura {i+1}: {valor}")
        time.sleep(0.3)
    
    # Análisis de los valores
    avg = sum(valores) / len(valores)
    min_val = min(valores)
    max_val = max(valores)
    
    print(f"\n--- RESULTADOS DEL DIAGNÓSTICO ---")
    print(f"Valor mínimo: {min_val}")
    print(f"Valor máximo: {max_val}")
    print(f"Valor promedio: {avg:.2f}")
    print(f"Rango: {max_val - min_val}")
    
    # Evaluación del rango esperado
    if avg < 800:
        print(" PROBLEMA GRAVE: Valores muy bajos")
        print("   - Verificar conexión de 3.3V y GND")
        print("   - Verificar electrodos conectados")
        print("   - Verificar cableado del sensor")
    elif avg < 1500:
        print("️  ALERTA: Valores más bajos de lo esperado")
        print("   - Posible mala conexión de electrodos")
        print("   - Verificar que sensor esté alimentado")
    elif avg > 3000:
        print("️  ALERTA: Valores muy altos - Posible saturación")
        print("   - Verificar conexión a 3.3V (no 5V)")
        print("   - Electrodos haciendo mal contacto")
    else:
        print(" Rango de valores dentro de lo esperado")
        
    if max_val - min_val < 50:
        print("  Señal muy plana - Verificar electrodos")
    else:
        print(" Variabilidad de señal OK")
    
    print("Recomendación: Los valores deberían variar entre 1500-2500 en reposo")

# Función de muestreo con timer
def muestrear_ecg(timer):
    valor = ecg_sensor.read()
    muestras.append(valor)
    
    # Mantener buffer para filtros (últimas 30 muestras)
    if len(muestras) > 30:
        muestras.pop(0)
    
    # Aplicar filtros
    aplicar_filtros(valor)

# Función para aplicar filtros digitales
def aplicar_filtros(valor_crudo):
    global datos_crudos, datos_promedio, datos_mediana, datos_exponencial
    
    # Señal cruda
    if filtros_activos['CRUDO']:
        datos_crudos.append(valor_crudo)
        if len(datos_crudos) > 500:
            datos_crudos.pop(0)
    
    # Filtro promedio móvil
    if filtros_activos['PROMEDIO'] and len(muestras) >= 5:
        promedio = sum(muestras[-5:]) / 5
        datos_promedio.append(promedio)
        if len(datos_promedio) > 500:
            datos_promedio.pop(0)
    
    # Filtro mediana
    if filtros_activos['MEDIANA'] and len(muestras) >= 5:
        mediana = sorted(muestras[-5:])[2]
        datos_mediana.append(mediana)
        if len(datos_mediana) > 500:
            datos_mediana.pop(0)
    
    # Filtro exponencial (IIR) - CORREGIDO
    if filtros_activos['EXPONENCIAL']:
        alpha = 0.3
        if len(datos_exponencial) > 0:
            exponencial = alpha * valor_crudo + (1 - alpha) * datos_exponencial[-1]
        else:
            exponencial = valor_crudo
        datos_exponencial.append(exponencial)
        if len(datos_exponencial) > 500:
            datos_exponencial.pop(0)
    
    # Control LED (parpadeo con señal)
    if len(datos_crudos) > 10:
        
        variacion = abs(datos_crudos[-1] - datos_crudos[-2]) if len(datos_crudos) > 1 else 0
        led.value(1 if variacion > 50 else 0)

# Función para configurar frecuencia de muestreo
def configurar_frecuencia(frecuencia):
    global frecuencia_muestreo
    frecuencia_muestreo = frecuencia
    timer_muestreo.deinit()
    
    periodo_ms = int(1000 / frecuencia)
    timer_muestreo.init(period=periodo_ms, mode=Timer.PERIODIC, callback=muestrear_ecg)
    
    print(f" Frecuencia configurada: {frecuencia} Hz")

# Función para guardar datos en archivo .txt
def guardar_datos_archivo():
    if len(datos_crudos) == 0:
        print(" No hay datos para guardar")
        return
    
    nombre_archivo = f"ecg_datos_{int(time.time())}.txt"
    
    try:
        with open(nombre_archivo, 'w') as archivo:
            archivo.write("Muestra,Crudo,Promedio,Mediana,Exponencial\n")
            
            min_longitud = min(len(datos_crudos), len(datos_promedio), 
                              len(datos_mediana), len(datos_exponencial))
            
            for i in range(min_longitud):
                crudo = datos_crudos[i] if i < len(datos_crudos) else 0
                promedio = datos_promedio[i] if i < len(datos_promedio) else 0
                mediana = datos_mediana[i] if i < len(datos_mediana) else 0
                exponencial = datos_exponencial[i] if i < len(datos_exponencial) else 0
                
                linea = f"{i+1},{crudo},{promedio},{mediana},{exponencial}\n"
                archivo.write(linea)
        
        print(f" Datos guardados en: {nombre_archivo}")
        print(f"   Muestras guardadas: {min_longitud}")
        
    except Exception as e:
        print(f" Error al guardar archivo: {e}")

# Función para mostrar datos en Serial Plotter
def mostrar_serial_plotter():
    if len(datos_crudos) == 0:
        print(" No hay datos para mostrar")
        return
    
    print("\n=== MODO SERIAL PLOTTER ===")
    print("Formato: Crudo,Promedio,Mediana,Exponencial")
    print("Presione Ctrl+C para detener...")
    
    # Encabezado para Serial Plotter 
    header = ""
    if filtros_activos['CRUDO']:
        header += "Crudo,"
    if filtros_activos['PROMEDIO']:
        header += "Promedio,"
    if filtros_activos['MEDIANA']:
        header += "Mediana,"
    if filtros_activos['EXPONENCIAL']:
        header += "Exponencial,"
    
    if header.endswith(','):
        header = header[:-1]
        
    
    print(header)
    
    try:
        min_longitud = min(300, len(datos_crudos), len(datos_promedio), 
                          len(datos_mediana), len(datos_exponencial))
        
        for i in range(min_longitud):
            linea = ""
            if filtros_activos['CRUDO'] and i < len(datos_crudos):
                linea += f"{datos_crudos[i]},"
            if filtros_activos['PROMEDIO'] and i < len(datos_promedio):
                linea += f"{datos_promedio[i]},"
            if filtros_activos['MEDIANA'] and i < len(datos_mediana):
                linea += f"{datos_mediana[i]},"
            if filtros_activos['EXPONENCIAL'] and i < len(datos_exponencial):
                linea += f"{datos_exponencial[i]},"
            
            if linea.endswith(','):
                linea = linea[:-1]
                
            print(linea)
            time.sleep(1.0 / frecuencia_muestreo)
            
    except KeyboardInterrupt:
        print("\n  Visualización detenida")
    except Exception as e:
        print(f" Error en visualización: {e}")

# Función para configurar filtros
def configurar_filtros():
    print("\n=== CONFIGURAR FILTROS ===")
    print("1. Crudo: " + (" ACTIVADO" if filtros_activos['CRUDO'] else " DESACTIVADO"))
    print("2. Promedio: " + (" ACTIVADO" if filtros_activos['PROMEDIO'] else " DESACTIVADO"))
    print("3. Mediana: " + (" ACTIVADO" if filtros_activos['MEDIANA'] else " DESACTIVADO"))
    print("4. Exponencial: " + (" ACTIVADO" if filtros_activos['EXPONENCIAL'] else " DESACTIVADO"))
    print("5.  TODOS ACTIVOS")
    print("6.  TODOS DESACTIVADOS")
    print("7.  SOLO CRUDO")
    print("8. ️  VOLVER")
    
    try:
        opcion = input("Seleccione opción: ").strip()
        if opcion == "1":
            filtros_activos['CRUDO'] = not filtros_activos['CRUDO']
        elif opcion == "2":
            filtros_activos['PROMEDIO'] = not filtros_activos['PROMEDIO']
        elif opcion == "3":
            filtros_activos['MEDIANA'] = not filtros_activos['MEDIANA']
        elif opcion == "4":
            filtros_activos['EXPONENCIAL'] = not filtros_activos['EXPONENCIAL']
        elif opcion == "5":
            for filtro in filtros_activos:
                filtros_activos[filtro] = True
            print(" Todos los filtros ACTIVADOS")
        elif opcion == "6":
            for filtro in filtros_activos:
                filtros_activos[filtro] = False
            print(" Todos los filtros DESACTIVADOS")
        elif opcion == "7":
            for filtro in filtros_activos:
                filtros_activos[filtro] = (filtro == 'CRUDO')
            print(" Solo señal CRUDA activada")
        elif opcion == "8":
            return
        else:
            print(" Opción no válida")
            return
            
        print(" Configuración actualizada")
        
    except Exception as e:
        print(f" Error en configuración: {e}")

# Función para ver estadísticas detalladas
def ver_estadisticas():
    print(f"\n=== ESTADÍSTICAS DETALLADAS ===")
    print(f" Frecuencia muestreo: {frecuencia_muestreo} Hz")
    print(f" Muestras crudas: {len(datos_crudos)}")
    print(f" Muestras promedio: {len(datos_promedio)}")
    print(f" Muestras mediana: {len(datos_mediana)}")
    print(f" Muestras exponencial: {len(datos_exponencial)}")
    
    if datos_crudos:
        print(f" Último valor crudo: {datos_crudos[-1]}")
        if len(datos_crudos) > 1:
            print(f" Rango de valores: {min(datos_crudos)} - {max(datos_crudos)}")
            print(f" Variabilidad: {max(datos_crudos) - min(datos_crudos)}")
    
    print("\n️  Filtros activos:")
    for filtro, activo in filtros_activos.items():
        estado = " ACTIVADO" if activo else " DESACTIVADO"
        print(f"   {filtro}: {estado}")

# Menú principal
def mostrar_menu():
    print("\n" + "="*60)
    print("SISTEMA ECG AVANZADO - ESP32 ")
    print("="*60)
    print("1. Iniciar adquisición en tiempo real")
    print("2. Configurar frecuencia de muestreo")
    print("3. Configurar filtros digitales")
    print("4. Mostrar en Serial Plotter")
    print("5. Guardar datos en archivo .txt")
    print("6. Ver estadísticas")
    print("7. Diagnóstico del sensor")
    print("8. Salir")
    print("="*60)

# Programa principal
print(" Inicializando sistema ECG...")
print(" Configurando sensor AD8232...")

# Diagnóstico inicial automático
print("\n--- DIAGNÓSTICO INICIAL AUTOMÁTICO ---")
diagnostico_sensor()

configurar_frecuencia(100)

print("\n Sistema listo. Use el menú para comenzar.")

while True:
    try:
        mostrar_menu()
        opcion = input("Seleccione opción: ").strip()
        
        if opcion == "1":
            print("\n️  Adquisición en tiempo real ACTIVA")
            print(" Los datos se están capturando...")
            print("️  Presione Ctrl+C para volver al menú")
            try:
                inicio = time.time()
                while True:
                    tiempo_transcurrido = time.time() - inicio
                    muestras_por_segundo = len(datos_crudos) / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
                    print(f"\r️  Tiempo: {int(tiempo_transcurrido)}s | Muestras: {len(datos_crudos)} | Frecuencia: {muestras_por_segundo:.1f} Hz", end="")
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n️  Volviendo al menú principal...")
            
        elif opcion == "2":
            print(f"\n  Frecuencia actual: {frecuencia_muestreo} Hz")
            try:
                nueva_frec = int(input("Nueva frecuencia (10-500 Hz): "))
                if 10 <= nueva_frec <= 500:
                    configurar_frecuencia(nueva_frec)
                else:
                    print(" Frecuencia fuera de rango (10-200 Hz)")
            except ValueError:
                print(" Valor inválido. Ingrese un número.")
                
        elif opcion == "3":
            configurar_filtros()
            
        elif opcion == "4":
            mostrar_serial_plotter()
            
        elif opcion == "5":
            guardar_datos_archivo()
            
        elif opcion == "6":
            ver_estadisticas()
            
        elif opcion == "7":
            diagnostico_sensor()
                
        elif opcion == "8":
            timer_muestreo.deinit()
            led.off()
            print("\n Sistema detenido. ¡Hasta luego! ")
            break
            
        else:
            print(" Opción no válida. Seleccione 1-8.")
            
    except KeyboardInterrupt:
        timer_muestreo.deinit()
        led.off()
        print("\n\n️  Sistema interrumpido por el usuario")
        break
    except Exception as e:
        print(f"\n Error inesperado: {e}")