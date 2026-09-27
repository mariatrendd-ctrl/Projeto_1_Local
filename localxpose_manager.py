"""
LOCALXPOSE MANAGER v14 - SIMPLES
- 6 tokens x 10 slots = 60 slots
- TODOS buscam na MESMA porta (sequencial)
- Achou conexão? TRAVA e não mexe em NADA
- Não achou? Espera 30s e busca de novo
- Tecla minuscula: libera | Tecla maiuscula: blacklist
- Conexão caiu? Remove blindagem automaticamente e volta a buscar
"""
import subprocess, threading, time, os, re, random, msvcrt, winsound, ctypes, atexit
from colorama import init
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich.layout import Layout
from rich.align import Align
from rich import box as rich_box

init(autoreset=True)
os.system("cls")
os.system("mode con cols=220 lines=60")
try: ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 3)
except: pass

LOCLX_EXE      = r"C:\loclx-windows-amd64\loclx.exe"
LOG_DIR        = r"C:\loclx-windows-amd64\endpoints"
BLACKLIST_FILE = r"C:\loclx-windows-amd64\blacklist.txt"
CONN_FILE      = r"C:\loclx-windows-amd64\token_conns.txt"
ENDPOINTS_FILE = r"C:\loclx-windows-amd64\endpoints_usados.txt"
PORTAS_FILE    = r"C:\loclx-windows-amd64\portas_usadas.txt"
REGIAO         = "us"
NUM_SLOTS      = 60
CICLO_SLOT     = 30
TOKENS = [
    "lHkQPl33gI84MxQIUoX7sr64jWHzbIHTQGpvMRQj",
    "",
    "",
    "",
    "",
    "",
]
_tk_r0 = 10
_tk_r1 = 20
_tk_r2 = 30
_tk_r3 = 40
_tk_r4 = 50
_tk_r5 = 60

def _token(s):
    if s <= _tk_r0: return TOKENS[0] if TOKENS[0] else None  # tk1: S01-S10 (10 slots)
    if s <= _tk_r1: return TOKENS[1] if TOKENS[1] else None  # tk2: S11-S20 (10 slots)
    if s <= _tk_r2: return TOKENS[2] if TOKENS[2] else None  # tk3: S21-S30 (10 slots)
    if s <= _tk_r3: return TOKENS[3] if TOKENS[3] else None  # tk4: S31-S40 (10 slots)
    if s <= _tk_r4: return TOKENS[4] if TOKENS[4] else None  # tk5: S41-S50 (10 slots)
    if s <= _tk_r5: return TOKENS[5] if TOKENS[5] else None  # tk6: S51-S60 (10 slots)
    return None

def _tk_idx(s):
    """Retorna o índice do token (0-5) ao qual o slot pertence"""
    if s <= _tk_r0: return 0
    if s <= _tk_r1: return 1
    if s <= _tk_r2: return 2
    if s <= _tk_r3: return 3
    if s <= _tk_r4: return 4
    return 5

def _porta_slot(s):
    """Retorna a porta configurada para o token do slot"""
    return tk_portas[_tk_idx(s)]
REGEX = re.compile(r'([\w.\-]+\.loclx\.io):(\d{4,5})', re.IGNORECASE)

console         = Console(force_terminal=True, highlight=False, legacy_windows=False, no_color=False)
lock            = threading.Lock()
slot_info       = {}
procs           = {}
conexoes_ativas = {}
letras_usadas   = {}
slots_liberar   = set()
slots_blindados = set()  # slots com conexão ativa — INTOCÁVEIS até R
portas_conectadas = {}  # {porta: [slot_nums]} - lista de slots conectados em cada porta
MAX_SLOTS_POR_PORTA = 1  # Apenas 1 slot por porta
LETRAS          = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
endpoints_usados= set()
portas_historico= set()  # portas já usadas — não repete enquanto arquivo existir
blacklist_eps   = set()
blacklist_flash = {}
porta_atual     = 0          # mantido para compatibilidade com display
proxima_porta   = 0
tempo_porta     = time.time()
tempo_inicio    = time.time()
# Porta por token: tk_portas[0..5] = porta atual de cada token
tk_portas       = [0, 0, 0, 0, 0, 0]
# Porta base escolhida na config (ponto de partida da sequência)
tk_portas_base  = [0, 0, 0, 0, 0, 0]
# Tempo de troca de porta em segundos (configurado na tela de config)
PORTA_TEMPO     = 60 * 60   # padrão 60 min, substituído na config
conn_count_real = 0
conn_rate_ts    = []
conn_rate_min   = 0
_inicio_event   = threading.Event()
_tcp_cache      = []
_tcp_lock       = threading.Lock()

def _cleanup():
    os.system("taskkill /F /IM loclx.exe >nul 2>&1")
atexit.register(_cleanup)
try:
    _H = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)
    _href = _H(lambda e: (_cleanup(), False)[1])
    ctypes.windll.kernel32.SetConsoleCtrlHandler(_href, True)
except: pass

SP=["\u25dc","\u25dd","\u25de","\u25df"]
SD=["\u28f7","\u28ef","\u28df","\u287f"]
SC=["\u25f4","\u25f5","\u25f6","\u25f7"]
B="\u2588"; V="\u2591"
CORES=["bold color(51)","bold color(46)","bold color(226)","bold color(129)",
       "bold color(196)","bold color(135)","bold color(93)","bold color(39)",
       "bold color(208)","bold color(118)"]

PORTA_SEQ_FILE = r"C:\loclx-windows-amd64\porta_seq.txt"
PORTA_SEQ_MIN  = 10
PORTA_SEQ_MAX  = 65535
porta_seq_atual = PORTA_SEQ_MIN

# ── Gerador de porta aleatória com distribuição 60/40 ──────────────────────
# 60% → 1000-9999   |   40% → 10000-49151
def _porta_aleatoria():
    """Gera porta aleatória: 60% faixa 1000-9999, 40% faixa 10000-49151"""
    if random.random() < 0.60:
        return random.randint(1000, 9999)
    else:
        return random.randint(10000, 49151)

def _carregar_seq():
    global porta_seq_atual
    try:
        v = open(PORTA_SEQ_FILE, encoding="utf-8").readline().strip()
        if v:
            p = int(v)
            if PORTA_SEQ_MIN <= p <= PORTA_SEQ_MAX:
                porta_seq_atual = p
    except: pass

def _salvar_seq():
    try:
        open(PORTA_SEQ_FILE, "w", encoding="utf-8").write(f"{porta_seq_atual}\n")
    except: pass

def _nova_porta():
    global porta_seq_atual
    p = porta_seq_atual
    porta_seq_atual += 1
    if porta_seq_atual > PORTA_SEQ_MAX:
        porta_seq_atual = PORTA_SEQ_MIN
    portas_historico.add(p)
    _salvar_seq()
    return p

def _beep_conn():
    try:
        for f in [1200,1500,1800,2000,1800,2000,2200]: winsound.Beep(f,90)
        time.sleep(0.08)
        for f in [2000,2200,2500]: winsound.Beep(f,130)
    except: pass

def _beep_bl():
    try:
        for f in [800,600,400]: winsound.Beep(f,100)
    except: pass

def _netstat_scan():
    try:
        out = subprocess.check_output(["netstat","-ano"],
            text=True, encoding="utf-8", errors="replace",
            timeout=8, creationflags=0x08000000)
        rows = []
        for ln in out.splitlines():
            ln = ln.strip()
            if not ln.startswith("TCP"): continue
            p = ln.split()
            if len(p) < 5: continue
            try:
                lport = int(p[1].rsplit(":",1)[-1])
                raddr = p[2]
                state = p[3]
                pid   = int(p[4])
                # Ignora entradas sem estado válido
                if state not in ("ESTABLISHED","LISTENING","TIME_WAIT",
                                 "CLOSE_WAIT","SYN_SENT","SYN_RECEIVED"):
                    continue
                rows.append((lport, raddr, pid, state))
            except: continue
        return rows
    except: return []

def _tcp_thread():
    global _tcp_cache
    while True:
        try:
            r = _netstat_scan()
            with _tcp_lock: _tcp_cache = r
        except: pass
        time.sleep(0.5)

def _tem_conexao_porta(porta):
    """ESTABLISHED na porta local — detecção simples via netstat"""
    with _tcp_lock: rows = list(_tcp_cache)
    for (lp, ra, pid, st) in rows:
        if st == "ESTABLISHED" and lp == porta:
            return True
    return False

def _tem_cliente_na_porta(porta):
    """
    Detecta cliente REAL conectado via túnel loclx.
    
    Estratégia dupla:
    1. loclx encaminha cliente → abre loopback para serviço local:
       qualquer porta efêmera  →  127.0.0.1:porta  (ESTABLISHED)
       Isso indica que o loclx está ativo encaminhando tráfego real.
    2. Conta quantas conexões ESTABLISHED existem na porta — se há
       mais de 1, certamente uma delas é de cliente real (além da
       própria conexão interna de keep-alive do loclx).
    """
    with _tcp_lock: rows = list(_tcp_cache)
    loopback_count = 0
    total_established = 0
    for (lp, ra, pid, st) in rows:
        if st != "ESTABLISHED": continue
        # Conta todas as ESTABLISHED saindo desta porta local
        if lp == porta:
            total_established += 1
        # Detecta loopback de encaminhamento: endereço remoto é 127.0.0.1:porta
        try:
            ra_port = int(ra.rsplit(":", 1)[-1])
            ra_host = ra.rsplit(":", 1)[0].strip("[]")
            if ra_port == porta and ra_host in ("127.0.0.1", "::1"):
                loopback_count += 1
        except: pass
    # Cliente real detectado se:
    # - há loopback de encaminhamento (loclx forwarding para o serviço), OU
    # - há mais de 1 ESTABLISHED na porta (loclx interno + cliente externo)
    return loopback_count > 0 or total_established > 1

def _pid_conexao_porta(porta):
    """Retorna o PID do processo com conexão ESTABLISHED na porta local, ou None"""
    with _tcp_lock: rows = list(_tcp_cache)
    for (lp, ra, pid, st) in rows:
        if st == "ESTABLISHED" and lp == porta:
            return pid
    return None

def _proc_tem_conn_estabelecida(pid, porta_local):
    """
    Detecta cliente real conectado ao túnel do loclx.
    Quando há cliente, o PID do loclx mostra ESTABLISHED com
    remote = 127.0.0.1:porta_local (encaminhamento para o serviço).
    """
    if not pid: return False
    with _tcp_lock: rows = list(_tcp_cache)
    for (lp, ra, p_pid, st) in rows:
        if st != "ESTABLISHED": continue
        if p_pid != pid: continue
        try:
            ra_host = ra.rsplit(":", 1)[0].strip("[]")
            ra_port = int(ra.rsplit(":", 1)[-1])
            if ra_host in ("127.0.0.1", "::1") and ra_port == porta_local:
                return True
        except: pass
    return False
def _carregar():
    global conn_count_real
    _carregar_seq()
    try:
        v=open(CONN_FILE,encoding="utf-8").readline().strip()
        if v: conn_count_real=int(v)
    except: pass
    try:
        for ln in open(ENDPOINTS_FILE,encoding="utf-8"):
            ep=ln.strip()
            if ep: endpoints_usados.add(ep)
    except: pass
    try:
        for ln in open(BLACKLIST_FILE,encoding="utf-8"):
            ep=ln.strip()
            if ep: blacklist_eps.add(ep)
    except: pass
    try:
        for ln in open(PORTAS_FILE,encoding="utf-8"):
            p=ln.strip()
            if p: portas_historico.add(int(p))
    except: pass

def _salvar():
    try: open(CONN_FILE,"w",encoding="utf-8").write(f"{conn_count_real}\n")
    except: pass
    try:
        with lock: eu=set(endpoints_usados)
        with open(ENDPOINTS_FILE,"w",encoding="utf-8") as f:
            for ep in sorted(eu): f.write(ep+"\n")
    except: pass
    try:
        with open(PORTAS_FILE,"w",encoding="utf-8") as f:
            for p in sorted(portas_historico): f.write(f"{p}\n")
    except: pass

def _rate_thread():
    global conn_rate_min
    while True:
        time.sleep(2)
        agora=time.time()
        with lock:
            while conn_rate_ts and agora-conn_rate_ts[0]>60: conn_rate_ts.pop(0)
            conn_rate_min=len(conn_rate_ts)

def _spawn_e_capturar(porta, slot_num):
    try:
        env = os.environ.copy()
        env["ACCESS_TOKEN"] = _token(slot_num)
        cmd = [LOCLX_EXE, "tunnel", "tcp", "--to", f"localhost:{porta}"]
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            bufsize=1, env=env, creationflags=0x08000000)
    except: return None, "", ""

    res=[None,None]; ev=threading.Event()
    # Flag de conexão de cliente — setada quando loclx imprime mensagem de cliente conectado
    p._conn_flag = threading.Event()
    p._conn_lines = []  # linhas de log para debug

    def _ler_stderr():
        try:
            for ln in iter(p.stderr.readline, ""):
                low = ln.lower()
                stripped = ln.strip()

                # Salva últimas linhas para diagnóstico
                p._conn_lines.append(stripped)
                if len(p._conn_lines) > 20: p._conn_lines.pop(0)

                # Erros de limite/auth — encerra
                if any(x in low for x in ["limit","unauthorized","invalid","denied","exceeded","too many"]):
                    ev.set(); return

                # Captura endpoint
                m = REGEX.search(ln)
                if m:
                    res[0]=m.group(1); res[1]=m.group(2)
                    ev.set()

                # Detecta cliente conectado — palavras que o loclx imprime quando
                # alguém usa o túnel para se conectar ao serviço local
                if any(x in low for x in ["accepted","new conn","connection from",
                                           "connected from","client connected",
                                           "forwarding","proxy","session"]):
                    p._conn_flag.set()

                if p.poll() is not None: break
        except: pass
        ev.set()

    def _drain(pipe):
        try:
            for _ in iter(pipe.readline, ""):
                if p.poll() is not None: break
        except: pass

    threading.Thread(target=_ler_stderr, daemon=True).start()
    threading.Thread(target=_drain, args=(p.stdout,), daemon=True).start()

    def _watchdog():
        while not ev.is_set():
            if p.poll() is not None: ev.set(); return
            time.sleep(0.2)
    threading.Thread(target=_watchdog, daemon=True).start()

    ev.wait(timeout=15)

    if res[0]:
        return p, res[0], res[1]
    try:
        p.terminate()
        p.wait(timeout=3)
    except: pass
    return None, "", ""

def _thread_slot(s):
    global conn_count_real
    _inicio_event.wait()
    time.sleep(0)
    proc=[None]

    def _matar():
        # Nunca mata se este slot esta blindado
        if s in slots_blindados:
            return
        if proc[0]:
            try:
                proc[0].terminate()
                proc[0].wait(timeout=3)
            except: pass
            proc[0]=None
        with lock: procs.pop(s,None)

    while True:
        # ── BLINDADO: slot com conexão ativa — ABSOLUTAMENTE intocável ──────────
        if s in slots_blindados:
            with lock:
                slot_info[s]["status"] = "conectado"
            time.sleep(1)
            continue

        # ── LIBERAR (só chega aqui se NÃO blindado) ─────────────────────────────
        with lock:
            liberar = s in slots_liberar
            if liberar: slots_liberar.discard(s)

        if liberar:
            _matar()
            with lock:
                letra=slot_info.get(s,{}).get("letra","")
                porta_lib=conexoes_ativas.get(s,{}).get("porta_local",0)
                letras_usadas.pop(letra,None)
                conexoes_ativas.pop(s,None)
                if porta_lib and porta_lib in portas_conectadas:
                    slots_na_porta = portas_conectadas.get(porta_lib, [])
                    if s in slots_na_porta: slots_na_porta.remove(s)
                    if not slots_na_porta: portas_conectadas.pop(porta_lib,None)
                slot_info[s].update({"status":"offline","host":"","porta":"","pid":0,"letra":""})
            time.sleep(0.3)
            continue

        # ── BUSCA ────────────────────────────────────────────────────────────────
        try:
            # Token desativado? Slot fica em standby
            if not _token(s):
                with lock: slot_info[s].update({"status":"offline","pid":0})
                time.sleep(5)
                continue

            _matar()
            porta_s = _porta_slot(s)   # porta do token deste slot

            with lock:
                slot_info[s]={"status":"subindo","host":"","porta":"",
                              "porta_local":porta_s,"letra":"","pid":0}

            p_novo,h,ep = _spawn_e_capturar(porta_s, s)

            if not h:
                with lock: slot_info[s].update({"status":"offline","pid":0})
                time.sleep(2)
                continue

            if p_novo is None or p_novo.poll() is not None:
                with lock: slot_info[s].update({"status":"offline","pid":0})
                time.sleep(2)
                continue

            proc[0]=p_novo
            ep_full=f"{h}:{ep}"
            conn_confirmacoes = [0]
            t_proc_inicio = time.time()  # momento em que o processo subiu

            if ep_full in blacklist_eps:
                _matar()
                with lock:
                    slot_info[s].update({"status":"blacklist","host":h,"porta":ep,"pid":0})
                    blacklist_flash[s]=time.time()
                threading.Thread(target=_beep_bl,daemon=True).start()
                time.sleep(3)
                with lock: slot_info[s].update({"status":"offline","host":"","porta":"","pid":0})
                continue

            with lock:
                procs[s]=p_novo
                slot_info[s].update({"status":"online","host":h,"porta":ep,
                                     "pid":p_novo.pid,"porta_local":porta_s,
                                     "_t_on":time.time()})
            t_on=time.time()

            # ── LOOP DE ESPERA POR CONEXÃO ────────────────────────────────────
            while True:
                # Blindado durante o loop? Sai imediatamente
                if s in slots_blindados:
                    break

                time.sleep(0.4)

                # Liberar?
                with lock:
                    lib2 = s in slots_liberar
                    if lib2: slots_liberar.discard(s)

                # Detecção via netstat por PID do processo deste slot.
                # Ignora os primeiros 3s após subir (conexões transitórias).
                # Requer 8 confirmações consecutivas (~3.2s) para registrar.
                _pid_s = proc[0].pid if proc[0] and proc[0].poll() is None else None
                _processo_estavel = (time.time() - t_proc_inicio) >= 3.0
                if _pid_s and _processo_estavel and _proc_tem_conn_estabelecida(_pid_s, porta_s):
                    conn_confirmacoes[0] += 1
                else:
                    conn_confirmacoes[0] = 0

                if conn_confirmacoes[0] >= 8:
                    registrado = False
                    with lock:
                        if s not in slots_blindados and s not in conexoes_ativas:
                            if porta_s not in portas_conectadas:
                                portas_conectadas[porta_s] = []
                            portas_conectadas[porta_s].append(s)
                            slot_info[s].update({"status":"conectado","letra":""})
                            conexoes_ativas[s]={"ep":ep_full,"porta_local":porta_s,
                                                "letra":"","tempo":time.time(),"visivel":True}
                            usadas=set(letras_usadas.keys())
                            letra=next((l for l in LETRAS if l not in usadas),"?")
                            if letra!="?": letras_usadas[letra]=s
                            slot_info[s].update({"letra":letra})
                            conexoes_ativas[s]["letra"] = letra
                            conn_count_real+=1
                            conn_rate_ts.append(time.time())
                            endpoints_usados.add(ep_full)
                            slots_blindados.add(s)  # BLINDAGEM IMEDIATA
                            registrado = True
                    if registrado:
                        threading.Thread(target=_beep_conn,daemon=True).start()
                        try:
                            os.makedirs(LOG_DIR,exist_ok=True)
                            with open(os.path.join(LOG_DIR,"endpoints_salvos.txt"),"a",encoding="utf-8") as f:
                                f.write(f"\n{'='*50}\n")
                                f.write(f"Data/Hora : {time.strftime('%d/%m/%Y %H:%M:%S')}\n")
                                f.write(f"Slot      : S{s:02d}  Porta: {porta_s}\n")
                                f.write(f"Endpoint  : {ep_full}\n{'='*50}\n")
                        except: pass
                        break
                    if lib2:
                        _matar()
                        with lock:
                            slot_info[s].update({"status":"offline","host":"","porta":"","pid":0,"letra":""})
                        break
                    # já registrado por outro thread — reseta contador
                    conn_confirmacoes[0] = 0

                # Sem conexão confirmada: verifica lib2 e timeout
                if lib2:
                    _matar()
                    with lock:
                        slot_info[s].update({"status":"offline","host":"","porta":"","pid":0,"letra":""})
                    break

                if proc[0] is None or proc[0].poll() is not None:
                    with lock:
                        slot_info[s].update({"status":"offline","pid":0})
                        procs.pop(s,None)
                    proc[0]=None
                    break

                # Timeout do ciclo — NUNCA derruba se já está blindado ou conectado
                if time.time()-t_on >= CICLO_SLOT:
                    if s in slots_blindados:
                        break  # blindado: sai do loop inner, loop outer cuida
                    with lock:
                        ja_conectado = s in conexoes_ativas
                    if ja_conectado:
                        break  # já registrado: sai do loop inner sem matar
                    _matar()
                    with lock:
                        slot_info[s].update({"status":"offline","pid":0})
                    time.sleep(5)
                    break

        except Exception:
            # Exceção na busca — NÃO reseta se blindado
            if s not in slots_blindados:
                try:
                    with lock: slot_info[s].update({"status":"offline","pid":0})
                except: pass
            time.sleep(2)

def _bar(pct, w=28, cor="bold color(51)"):
    t=Text(); p=int(pct/100*w)
    for i in range(w): t.append(B if i<p else V, style=cor if i<p else "color(238)")
    return t

def _linha_slot(s, frame):
    with lock:
        info=slot_info.get(s,{}); conn=conexoes_ativas.get(s)
    st=info.get("status","offline"); host=info.get("host",""); ep_p=info.get("porta","")
    letra=info.get("letra",""); sid=f"S{s:02d}"
    if conn:
        ep=conn.get("ep","---"); t_c=int(time.time()-conn.get("tempo",time.time()))
        pl=str(conn.get("porta_local",porta_atual))
        mins=t_c//60; segs=t_c%60
        visivel=conn.get("visivel",True)

        if st == "reconectando":
            # Slot ativo mas recriando processo — mostra com spinner diferente
            ic = SD[frame%4]
            cor_s = "color(208)"
            t=Text(no_wrap=True)
            t.append(f"{ic}[{sid}{letra}] ",style=f"bold {cor_s}")
            t.append(f"{ep} ",style=f"{cor_s}")
            t.append(f":{pl} ",style="color(245)")
            t.append(f"{mins:02d}:{segs:02d} ",style="color(245)")
            t.append("recn",style="bold color(208)")
            return t
        
        if visivel:
            ic=["\u26a1","\u2605","\u26a1","\u2605"][frame%4]
            cor_s=CORES[(s-1)%len(CORES)]
        else:
            ic="\u25cf"
            cores_suaves=["color(93)","color(135)","color(129)","color(208)","color(39)","color(118)"]
            cor_s=cores_suaves[(s-1)%len(cores_suaves)]
        
        t=Text(no_wrap=True)
        t.append(f"{ic}[{sid}{letra}] ",style=f"bold {cor_s}")
        t.append(f"{ep} ",style=f"{cor_s}")
        t.append(f":{pl} ",style="color(245)")
        t.append(f"{mins:02d}:{segs:02d}",style="color(46)" if visivel else "color(245)")
        return t
    elif st=="online":
        pl=str(info.get("porta_local",porta_atual))
        ep=f"{host}:{ep_p}" if host else "---"
        with lock: t_on=slot_info.get(s,{}).get("_t_on",time.time())
        resto=max(0,CICLO_SLOT-int(time.time()-t_on))
        t=Text(no_wrap=True)
        t.append(f"{SP[frame%4]}[{sid}] ",style="bold color(51)")
        t.append(f"{ep} ",style="color(51)")
        t.append(f":{pl} ",style="color(245)")
        t.append(f"{resto}s",style="color(245)")
        return t
    elif st=="subindo":
        pl=str(info.get("porta_local",porta_atual))
        t=Text(no_wrap=True)
        t.append(f"{SD[frame%4]}[{sid}] ",style="color(33)")
        t.append("subindo... ",style="color(33)"); t.append(f":{pl}",style="color(245)")
        return t
    elif st=="aguardando":
        pl=str(info.get("porta_local",porta_atual))
        t=Text(no_wrap=True)
        t.append(f"\u23f8[{sid}] ",style="color(245)")
        t.append("aguard.. ",style="color(245)"); t.append(f":{pl}",style="color(245)")
        return t
    elif st=="blacklist":
        ep_bl=f"{host}:{ep_p}" if host and ep_p else "---"; t=Text(justify="center",no_wrap=True)
        if frame%2==0: t.append("\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab\U0001f6ab",style="bold color(226)")
        else: t.append(f" {ep_bl} ",style="bold color(226)")
        return t
    else:
        pl=str(info.get("porta_local",porta_atual))
        t=Text(no_wrap=True)
        t.append(f"\u2715[{sid}] ",style="color(238)")
        t.append("offline ",style="color(238)"); t.append(f":{pl}",style="color(245)")
        return t

def _tela(frame):
    with lock:
        _sl=dict(slot_info); _cn=dict(conexoes_ativas)
        _pa=porta_atual; _tk_p=list(tk_portas); _ti=tempo_inicio
        _cr=conn_count_real; _rm=conn_rate_min; _bl=len(blacklist_eps)
        _tp=tempo_porta; _pt=PORTA_TEMPO
    dec=int(time.time()-_ti)
    timer=f"{dec//3600:02d}:{(dec%3600)//60:02d}:{dec%60:02d}"
    rest=max(0,int(_pt-(time.time()-_tp)))
    cd=f"{rest//3600:02d}:{(rest%3600)//60:02d}:{rest%60:02d}" if rest>=3600 else f"{rest//60:02d}:{rest%60:02d}"
    n_on=sum(1 for v in _sl.values() if v.get("status")=="online")
    n_sub=sum(1 for v in _sl.values() if v.get("status")=="subindo")
    n_off=sum(1 for v in _sl.values() if v.get("status")=="offline")
    n_c=len(_cn)
    # Ranges dos tokens (lidos do escopo global)
    r0=_tk_r0; r1=_tk_r1; r2=_tk_r2; r3=_tk_r3; r4=_tk_r4; r5=_tk_r5

    hdr=Text(justify="center")
    hdr.append(f" {SC[frame%4]} LOCALXPOSE MANAGER ",style="bold bright_white on color(54)")
    # Mostra porta de cada token ativo
    for i in range(6):
        if TOKENS[i]:
            hdr.append(f"  TK{i+1}:{_tk_p[i]} ",style="bold white on color(22)")
    hdr.append(f"  troca: {cd}  ",style="color(51)")
    hdr.append(f"  {n_on} online  ",style="bold color(46)")
    hdr.append(f"conns: {_cr}  ",style="bold color(226)")
    if _rm>0:
        hdr.append(f"{_rm}/min  ",style="color(196)" if _rm>=150 else "color(226)" if _rm>=70 else "color(46)")
    hdr.append(f"{timer}  ",style="color(245)")
    hdr.append(f"\u26d4{_bl}blk",style="color(196)")

    def _border(s): return "color(118)" if s in _cn else "color(237)"
    def _col(r):
        tbl=Table(box=None,padding=(0,0),expand=True,show_header=False,show_edge=False)
        tbl.add_column(no_wrap=True)
        for s in r:
            tbl.add_row(Panel(_linha_slot(s,frame),border_style=_border(s),padding=(0,0),expand=True))
        return tbl

    col1=_col(range(1,r0+1)); col2=_col(range(r0+1,r1+1)); col3=_col(range(r1+1,r2+1))
    col4=_col(range(r2+1,r3+1)); col5=_col(range(r3+1,r4+1)); col6=_col(range(r4+1,r5+1))

    ic=["\u26a1","\U0001f525","\U0001f4a1","\U0001f31f","\U0001f4a5","\U0001f680"][frame%6]
    st_l=Text(justify="center")
    st_l.append(f" {ic} ",style="color(226)"); st_l.append("STATUS GERAL",style="bold color(51)")
    st_l.append(f" {ic} ",style="color(226)"); st_l.append(f"  \u25cf{n_on}",style="bold color(46)")
    st_l.append(f" online  ",style="color(46)"); st_l.append(f"\u25cf{n_sub}",style="color(33)")
    st_l.append(f" sub  ",style="color(33)"); st_l.append(f"\u25cf{n_off}",style="color(238)")
    st_l.append(f" off",style="color(238)")

    pct_c=min(int(_cr/max(_cr+1,10)*100),100) if _cr>0 else 0
    bc=Text(); bc.append(" \u25b6 CONNS ",style="color(226)")
    bc.append_text(_bar(pct_c,28,"color(226)")); bc.append(f" {_cr}",style="bold color(226)")

    pct_p=min(int((1-rest/max(_pt,1))*100),100)
    bp=Text(); bp.append(" \u25b6 PORTA ",style="color(135)")
    bp.append_text(_bar(pct_p,28,"color(135)")); bp.append(f" {pct_p}% {cd}",style="color(135)")

    # Barra de portas por token
    import random as _rnd; rng=_rnd.Random(frame*7+13)
    CIF=["color(236)","color(238)","color(240)","color(242)","color(245)"]
    tk_t=Text(no_wrap=True)
    n_tk_ativos = sum(1 for t in TOKENS if t)
    tk_t.append(f"{n_tk_ativos} tokens ",style="bold color(129)")
    for ci in range(10):
        tk_t.append("$",style="color(129)" if (ci+frame)%3==0 else rng.choice(CIF))
    # Mostra portas de cada token ativo
    for i in range(6):
        if TOKENS[i]:
            tk_t.append(f"  TK{i+1}:", style="color(245)")
            tk_t.append(f"{_tk_p[i]}", style="bold color(129)")
    tk_t.append(f"  {_cr} conns",style="bold color(129)")
    if _rm>0: tk_t.append(f"  {_rm}/min",style="color(196)" if _rm>=150 else "color(226)" if _rm>=70 else "color(129)")
    tk_t.append(f"  {n_c}/{NUM_SLOTS} slots",style="bold color(46)")

    AT=["\U0001f4a1 ATIVOS \U0001f4a1","\u26a1 ATIVOS \u26a1","\U0001f31f ATIVOS \U0001f31f","\U0001f4a5 ATIVOS \U0001f4a5"]
    # Filtra apenas slots visíveis
    cn_visiveis = {s:c for s,c in _cn.items() if c.get("visivel", True)}
    n_c_vis = len(cn_visiveis)
    at_title=f"[bold color(51)] {AT[frame%4]} [{n_c_vis}] [/]" if n_c_vis else f"[color(238)] {AT[frame%4]} [/]"

    def _la(s,c):
        cor=CORES[(s-1)%len(CORES)]; ep=c.get("ep","---"); letra=c.get("letra","?")
        pl=str(c.get("porta_local",_pa)); t_c=int(time.time()-c.get("tempo",time.time()))
        mins=t_c//60; segs=t_c%60; ep_p=ep.split(":")[-1] if ":" in ep else ep
        ic2=["\u26a1","\u2605","\u26a1","\u2605"][frame%4]; t=Text(no_wrap=True)
        t.append(f"{ic2}",style=f"bold {cor}"); t.append(f"S{s:02d}",style="bold white")
        t.append(f":{ep_p}",style=f"bold {cor}"); t.append(f":{pl} ",style="color(245)")
        t.append(f"{mins:02d}:{segs:02d} ",style="bold color(46)")
        t.append(f"{letra.upper()}",style="bold color(226)"); t.append(f"{letra.lower()}",style=f"bold {cor}")
        return t

    at_tbl=Table(box=rich_box.SIMPLE,padding=(0,0),expand=True,show_header=False,show_edge=False,pad_edge=False,show_lines=True)
    at_tbl.add_column(no_wrap=True,ratio=1); at_tbl.add_column(no_wrap=True,ratio=1)
    al=sorted(cn_visiveis.items(),key=lambda x:x[0])  # Usa apenas visíveis
    for i in range(0,max(len(al),1),2):
        c1=_la(*al[i]) if i<len(al) else Text("")
        c2=_la(*al[i+1]) if i+1<len(al) else Text("")
        at_tbl.add_row(c1,c2)

    inst=Text(justify="center")
    inst.append("ESC",style="bold color(196)"); inst.append(" sair   ",style="color(245)")
    inst.append("a..z",style="bold color(226)"); inst.append(" liberar slot ativo   ",style="color(245)")
    inst.append("P",style="bold color(226)"); inst.append(" parar busca   ",style="color(245)")
    inst.append("R",style="bold color(51)"); inst.append(" reiniciar todos",style="color(245)")

    rt=Table(box=None,padding=(0,0),expand=True,show_header=False,show_edge=False)
    rt.add_column(no_wrap=True)
    rt.add_row(Panel(st_l,border_style="color(54)",padding=(0,1)))
    rt.add_row(Panel(bp,border_style="color(54)",padding=(0,1)))
    rt.add_row(Panel(bc,border_style="color(54)",padding=(0,1)))
    rt.add_row(Panel(tk_t,border_style="color(54)",padding=(0,1),title="[color(245)] TOKENS / PORTAS [/]"))
    rt.add_row(Panel(at_tbl,border_style="color(54)",padding=(0,0),title=at_title))
    rt.add_row(Panel(inst,border_style="color(54)",padding=(0,0)))

    layout=Layout()
    layout.split(Layout(name="h",size=3),Layout(name="b"))
    layout["b"].split_row(Layout(name="c1",ratio=2),Layout(name="c2",ratio=2),
                          Layout(name="c3",ratio=2),Layout(name="c4",ratio=2),
                          Layout(name="c5",ratio=2),Layout(name="c6",ratio=2),
                          Layout(name="r",ratio=3))
    layout["h"].update(Panel(Align.center(hdr),border_style="color(54)",padding=(0,0)))
    layout["c1"].update(Panel(col1,border_style="color(54)",padding=(0,0),title=f"[color(245)] S01-S{r0:02d} tk1 ({r0}) [/]"))
    layout["c2"].update(Panel(col2,border_style="color(54)",padding=(0,0),title=f"[color(245)] S{r0+1:02d}-S{r1:02d} tk2 ({r1-r0}) [/]"))
    layout["c3"].update(Panel(col3,border_style="color(54)",padding=(0,0),title=f"[color(245)] S{r1+1:02d}-S{r2:02d} tk3 ({r2-r1}) [/]"))
    layout["c4"].update(Panel(col4,border_style="color(54)",padding=(0,0),title=f"[color(245)] S{r2+1:02d}-S{r3:02d} tk4 ({r3-r2}) [/]"))
    layout["c5"].update(Panel(col5,border_style="color(54)",padding=(0,0),title=f"[color(245)] S{r3+1:02d}-S{r4:02d} tk5 ({r4-r3}) [/]"))
    layout["c6"].update(Panel(col6,border_style="color(54)",padding=(0,0),title=f"[color(245)] S{r4+1:02d}-S{r5:02d} tk6 ({r5-r4}) [/]"))
    layout["r"].update(Panel(rt,border_style="color(54)",padding=(0,0)))
    return layout

def _tela_config():
    """
    Tela de configuração inicial.
    Cada token tem seu próprio campo de porta + campo de tempo de troca.
    Navegação: ↑↓ entre tokens | SPACE ativar/desativar | +/- ajustar slots
               ← → ajusta porta -1/+1 | T digitar porta | M digitar minutos
               ENTER iniciar | ESC sair
    Retorna (slots_por_tk, ativos, portas_por_tk[6], minutos_troca)
    """
    global NUM_SLOTS, TOKENS
    slots  = [10, 10, 10, 10, 10, 10]
    ativos = [bool(TOKENS[0]), bool(TOKENS[1]), bool(TOKENS[2]),
              bool(TOKENS[3]), bool(TOKENS[4]), bool(TOKENS[5])]

    # Portas iniciam aleatórias: 60% faixa 1000-9999, 40% faixa 10000-49151
    portas = [_porta_aleatoria() for _ in range(6)]

    selecionado = 0
    digitando   = None   # None | "porta" | "minutos"
    buf         = ""
    minutos     = 60     # padrão 60 minutos

    PORTA_MIN = 1000
    PORTA_MAX = 49151

    def _ajusta(idx, delta):
        p = portas[idx] + delta
        if p < PORTA_MIN: p = PORTA_MAX
        if p > PORTA_MAX: p = PORTA_MIN
        portas[idx] = p

    def _faixa_label(porta):
        """Indica de qual faixa é a porta"""
        if 1000 <= porta <= 9999:
            return "60%"
        elif 10000 <= porta <= 49151:
            return "40%"
        return "   "

    def _render():
        os.system("cls")
        total = sum(slots[i] for i in range(6) if ativos[i])
        print("\n")
        print("  ╔══════════════════════════════════════════════════════════════════╗")
        print("  ║          ⚡  LOCALXPOSE MANAGER - CONFIG  ⚡                    ║")
        print("  ╠══════════════════════════════════════════════════════════════════╣")
        print("  ║   TOKEN   SLOTS   FAIXA         PORTA LOCAL   RANGE             ║")
        print("  ╠══════════════════════════════════════════════════════════════════╣")
        acum = 0
        for i in range(6):
            sel_tk  = "►" if i == selecionado else " "
            ativo   = "[X]" if ativos[i] else "[ ]"
            tk_nome = f"TK{i+1}"
            s_str   = f"{slots[i]:2d} sl"
            if ativos[i]:
                ini  = acum + 1
                fim  = acum + slots[i]
                acum = fim
                faixa = f"S{ini:02d}-S{fim:02d}"
            else:
                faixa = "desativ."

            if i == selecionado and digitando == "porta":
                p_disp = (buf + "█")[:7]
                fl = "   "
            else:
                p_disp = str(portas[i]) if ativos[i] else "  ---"
                fl = _faixa_label(portas[i]) if ativos[i] else "   "

            nav = " ←→" if (i == selecionado and ativos[i] and digitando is None) else "   "
            n_hint = " [N=nova]" if (i == selecionado and ativos[i] and digitando is None) else "         "
            print(f"  ║  {sel_tk} {ativo} {tk_nome}   {s_str}   {faixa:<10s}  {p_disp:>6s}{nav}  {fl}{n_hint}  ║")

        print("  ╠══════════════════════════════════════════════════════════════════╣")
        print(f"  ║  Total: {total} slots    Faixas: 60% = 1000-9999  |  40% = 10000-49151  ║")
        print("  ╠══════════════════════════════════════════════════════════════════╣")
        if digitando == "minutos":
            min_disp = buf + "█"
        else:
            min_disp = str(minutos)
        print(f"  ║  ► TEMPO DE TROCA DE PORTA: {min_disp:<4s} min                          ║")
        print("  ╠══════════════════════════════════════════════════════════════════╣")
        print("  ║  ↑↓ navegar    SPACE ativar/desativar   +/- ajustar slots       ║")
        print("  ║  N nova porta aleatória   ← → ajustar porta   T digitar porta   ║")
        print("  ║  M digitar minutos   ENTER iniciar   ESC sair                   ║")
        print("  ╚══════════════════════════════════════════════════════════════════╝")

    while True:
        _render()
        tecla = msvcrt.getch()

        # ── Modo digitação ───────────────────────────────────────────────────
        if digitando is not None:
            if tecla in (b'\r', b'\n'):
                if digitando == "porta":
                    try:
                        v = int(buf)
                        if 1 <= v <= 65535:
                            portas[selecionado] = v
                    except: pass
                elif digitando == "minutos":
                    try:
                        v = int(buf)
                        if 1 <= v <= 9999: minutos = v
                    except: pass
                digitando = None; buf = ""
            elif tecla == b'\x1b':
                digitando = None; buf = ""
            elif tecla == b'\x08':
                buf = buf[:-1]
            elif tecla.isdigit() and len(buf) < 5:
                buf += tecla.decode("ascii")
            continue

        # ── Navegação normal ─────────────────────────────────────────────────
        if tecla == b'\r':
            break

        elif tecla == b'\x1b':
            os.system("cls"); exit(0)

        elif tecla == b'\xe0':
            tecla2 = msvcrt.getch()
            if   tecla2 == b'H': selecionado = (selecionado - 1) % 6
            elif tecla2 == b'P': selecionado = (selecionado + 1) % 6
            elif tecla2 == b'K':
                if ativos[selecionado]: _ajusta(selecionado, -1)
            elif tecla2 == b'M':
                if ativos[selecionado]: _ajusta(selecionado, +1)

        elif tecla == b' ':
            ativos[selecionado] = not ativos[selecionado]

        elif tecla in (b'+', b'='):
            if slots[selecionado] < 10: slots[selecionado] += 1

        elif tecla in (b'-', b'_'):
            if slots[selecionado] > 1:  slots[selecionado] -= 1

        elif tecla in (b'N', b'n'):
            # Nova porta aleatória para o token selecionado (60/40)
            if ativos[selecionado]:
                portas[selecionado] = _porta_aleatoria()

        elif tecla in (b'T', b't'):
            if ativos[selecionado]:
                digitando = "porta"; buf = ""
                # Nota: digitação manual aceita 1-65535

        elif tecla in (b'M', b'm'):
            digitando = "minutos"; buf = ""

    return slots, ativos, list(portas), minutos

def main():
    global porta_atual, proxima_porta, tempo_porta, NUM_SLOTS, TOKENS
    global tk_portas, tk_portas_base, PORTA_TEMPO
    _carregar()

    # ── TELA DE CONFIGURAÇÃO ─────────────────────────────────────────────────
    slots_cfg, ativos_cfg, portas_cfg, minutos_cfg = _tela_config()

    for i in range(6):
        if not ativos_cfg[i]: TOKENS[i] = ""

    ranges = []
    acum = 0
    for i in range(6):
        if ativos_cfg[i]: acum += slots_cfg[i]
        ranges.append(acum)
    NUM_SLOTS = ranges[5]

    global _tk_r0, _tk_r1, _tk_r2, _tk_r3, _tk_r4, _tk_r5
    _tk_r0, _tk_r1, _tk_r2 = ranges[0], ranges[1], ranges[2]
    _tk_r3, _tk_r4, _tk_r5 = ranges[3], ranges[4], ranges[5]

    # Aplica portas por token e tempo de troca
    PORTA_TEMPO     = minutos_cfg * 60
    tk_portas       = list(portas_cfg)
    tk_portas_base  = list(portas_cfg)   # guarda ponto de partida da sequência
    porta_atual     = tk_portas[0]
    tempo_porta     = time.time()
    threading.Thread(target=_rate_thread,daemon=True).start()
    threading.Thread(target=_tcp_thread,daemon=True).start()
    def _auto_salvar():
        while True: time.sleep(30); _salvar()
    threading.Thread(target=_auto_salvar,daemon=True).start()

    os.system("cls")
    ctypes.windll.kernel32.SetConsoleTitleW(f"LOCALXPOSE MANAGER  |  TK1:{tk_portas[0]}")
    portas_display = "  ".join(
        f"TK{i+1}:{tk_portas[i]}" for i in range(6) if TOKENS[i]
    )
    console.print(Panel(
        f"\n[bold white on color(54)]   {portas_display}   [/]\n\n"
        f"[white]  Configure seu programa para a porta do token correspondente.[/]\n\n"
        f"[bold color(129)]  Iniciando {NUM_SLOTS} slots (6 tokens)...[/]\n",
        border_style="bold color(129)",expand=False,
        title="[bold white]\u26a1  LOCALXPOSE MANAGER  \u26a1[/]"))

    os.system("taskkill /F /IM loclx.exe >nul 2>&1")
    time.sleep(15)
    os.system("taskkill /F /IM loclx.exe >nul 2>&1")
    time.sleep(15)

    for s in range(1,NUM_SLOTS+1):
        slot_info[s]={"status":"offline","host":"","porta":"","porta_local":porta_atual,"letra":"","pid":0}
        threading.Thread(target=_thread_slot,args=(s,),daemon=True).start()

    _inicio_event.set()
    while msvcrt.kbhit(): msvcrt.getch()

    try:
        LF=32
        class CFI(ctypes.Structure):
            _fields_=[("cbSize",ctypes.c_ulong),("nFont",ctypes.c_ulong),
                      ("dwFontSize",ctypes.c_long*2),("FontFamily",ctypes.c_uint),
                      ("FontWeight",ctypes.c_uint),("FaceName",ctypes.c_wchar*LF)]
        f=CFI(); f.cbSize=ctypes.sizeof(CFI); f.nFont=12
        f.dwFontSize[0]=7; f.dwFontSize[1]=14; f.FontFamily=54; f.FontWeight=400; f.FaceName="Consolas"
        ctypes.windll.kernel32.SetCurrentConsoleFontEx(ctypes.windll.kernel32.GetStdHandle(-11),False,ctypes.byref(f))
    except: pass

    frame=0; _sair=[False]
    def _sz():
        try:
            import shutil; s=shutil.get_terminal_size(); return (s.columns,s.lines)
        except: return (220,50)
    _last=_sz()

    def _run():
        nonlocal frame,_last
        global porta_atual, proxima_porta, tempo_porta
        try: 
            rend=_tela(frame)
        except Exception as e:
            rend=Text(f"Erro ao renderizar: {e}")
        
        try:
            lc=Live(rend,console=console,screen=True,auto_refresh=False,
                    transient=False,redirect_stdout=False,redirect_stderr=False)
        except Exception as e:
            console.print(f"[red]Erro ao criar Live: {e}[/]")
            time.sleep(0.5)
            return

        with lc as live:
            while not _sair[0]:
                cur=_sz()
                if cur!=_last:
                    _last=cur
                    try: console.clear()
                    except: pass
                    return
                
                try: 
                    nova_tela = _tela(frame)
                    live.update(nova_tela, refresh=True)
                except Exception as e:
                    try:
                        live.update(Text(f"Erro: {e}"), refresh=True)
                    except:
                        pass
                
                frame+=1

                # ── Troca de porta por token quando o tempo vence ────────────
                if time.time() - tempo_porta >= PORTA_TEMPO:
                    with lock:
                        # Slots blindados (com conexão ativa) ficam na porta atual
                        # Os demais recebem nova porta aleatória (60/40)
                        portas_com_ativo = {
                            conexoes_ativas[s]["porta_local"]
                            for s in conexoes_ativas
                        }
                        for i in range(6):
                            if not TOKENS[i]: continue
                            tk_portas[i] = _porta_aleatoria()
                        porta_atual = tk_portas[0]
                        # Limpa portas_conectadas para portas sem ativo
                        for p in list(portas_conectadas.keys()):
                            if p not in portas_com_ativo:
                                portas_conectadas.pop(p, None)
                    tempo_porta = time.time()
                    titulo = "  ".join(
                        f"TK{i+1}:{tk_portas[i]}" for i in range(6) if TOKENS[i]
                    )
                    ctypes.windll.kernel32.SetConsoleTitleW(
                        f"LOCALXPOSE MANAGER  |  {titulo}"
                    )

                if msvcrt.kbhit():
                    tecla=msvcrt.getch()
                    if tecla==b"\x1b":
                        _cleanup(); _sair[0]=True; break
                    
                    # Tecla P: para slots sem conexão, NUNCA toca em blindados
                    if tecla in (b"P", b"p"):
                        with lock:
                            for s in range(1, NUM_SLOTS+1):
                                if s in slots_blindados:
                                    continue  # BLINDADO: intocável
                                slots_liberar.add(s)
                        try: winsound.Beep(1000, 200)
                        except: pass
                        continue

                    # Tecla R: REINICIA TUDO - remove blindagem de todos
                    if tecla in (b"R", b"r"):
                        with lock:
                            slots_blindados.clear()
                            for s in list(conexoes_ativas.keys()):
                                letra = slot_info.get(s, {}).get("letra", "")
                                if letra:
                                    letras_usadas.pop(letra, None)
                                conexoes_ativas.pop(s, None)
                                slots_liberar.add(s)
                        try: winsound.Beep(1500, 200)
                        except: pass
                        continue

                    # Letra minúscula: libera slot ativo individual (volta pra busca)
                    try: char = tecla.decode("ascii")
                    except: char = ""
                    if char.islower() and char not in ("p","r"):
                        with lock:
                            # Acha o slot que tem esta letra
                            slot_alvo = letras_usadas.get(char.upper())
                            if slot_alvo and slot_alvo in slots_blindados:
                                # Remove blindagem — slot sai sozinho na próxima iteração
                                slots_blindados.discard(slot_alvo)
                                letra_s = slot_info.get(slot_alvo,{}).get("letra","")
                                letras_usadas.pop(letra_s, None)
                                conexoes_ativas.pop(slot_alvo, None)
                                porta_lib = slot_info.get(slot_alvo,{}).get("porta_local",0)
                                if porta_lib and porta_lib in portas_conectadas:
                                    portas_conectadas.pop(porta_lib, None)
                                slot_info[slot_alvo].update({"status":"offline","host":"","porta":"","pid":0,"letra":""})
                                # NÃO adiciona ao slots_liberar — o loop blindado detecta sozinho
                        try: winsound.Beep(800, 150)
                        except: pass
                        continue

                time.sleep(0.3)

    while not _sair[0]: _run()
    os.system("cls"); _salvar()
    console.print("\n[bold color(129)] \u2713 LOCALXPOSE MANAGER encerrado.[/]\n")

if __name__=="__main__": main()
