import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.border.MatteBorder;
import javax.swing.text.BadLocationException;
import javax.swing.text.SimpleAttributeSet;
import javax.swing.text.StyleConstants;
import javax.swing.text.StyledDocument;
import java.awt.*;
import java.awt.datatransfer.StringSelection;
import java.awt.event.FocusAdapter;
import java.awt.event.FocusEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.awt.image.BufferedImage;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.io.Writer;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URI;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BooleanSupplier;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Turbo EA control panel - a desktop window that runs the backend (FastAPI /
 * uvicorn) and the frontend (Vite) for local development: live logs, editable
 * ports, start / stop / restart, a keep-running switch that restarts an app
 * when it crashes, and a Settings dialog that edits backend/.env.
 *
 * Plain Swing, no dependencies. Launched by panel.cmd / panel.sh at the
 * repository root, which compile it first. It stops only processes it started
 * itself, or a leftover Turbo EA process the user asks it to stop; another
 * app on the same port is never touched (see Ports.isOurs).
 *
 * The backend reads its configuration with os.getenv only - nothing loads a
 * .env file for it - so the panel parses backend/.env and passes every entry
 * as an environment variable to uvicorn.
 */
public class ControlPanel {

    static final boolean WINDOWS = System.getProperty("os.name").toLowerCase(Locale.ROOT).contains("win");
    static final String TITLE = "Turbo EA control panel";
    static final String ELLIPSIS = "…";
    static final int LOG_LIMIT = 5000;
    static final long STABLE_UPTIME_MS = 60_000;
    static final int MAX_CRASH_STREAK = 6;

    static final ScheduledExecutorService TIMER = Executors.newScheduledThreadPool(2, daemon("panel-timer"));
    static final ExecutorService ASYNC = Executors.newCachedThreadPool(daemon("panel-async"));

    public static void main(String[] args) {
        Path start = args.length > 0 ? Paths.get(args[0]) : Paths.get(System.getProperty("user.dir"));
        Path root = findRoot(start);
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception ignored) {
            // The default look and feel is fine.
        }
        if (root == null) {
            fatal("Could not find the Turbo EA repository (backend/app and frontend/src) from " + start.toAbsolutePath() + ".");
            return;
        }

        Path home = root.resolve("tools").resolve("control-panel");
        Path runtime = home.resolve(".runtime");
        if (!lockSingleInstance(runtime)) {
            fatal("The Turbo EA control panel is already open.");
            return;
        }

        Settings settings = new Settings(home.resolve("settings.local.properties"));
        EnvFile env = new EnvFile(root.resolve("backend").resolve(".env"));
        BackendApp backend = new BackendApp(root, settings, env);
        FrontendApp frontend = new FrontendApp(root, settings, backend);
        List<ManagedApp> apps = List.of(backend, frontend);

        // Covers the window being closed hard, or the session ending.
        Runtime.getRuntime().addShutdownHook(new Thread(() -> apps.forEach(ManagedApp::killNow)));

        SwingUtilities.invokeLater(() -> new MainWindow(root, apps, env, backend).setVisible(true));
        TIMER.scheduleWithFixedDelay(() -> apps.forEach(ManagedApp::poll), 1, 2, TimeUnit.SECONDS);
    }

    static Path findRoot(Path from) {
        for (Path p = from.toAbsolutePath().normalize(); p != null; p = p.getParent()) {
            if (Files.isDirectory(p.resolve("backend").resolve("app")) && Files.isDirectory(p.resolve("frontend").resolve("src"))) {
                return p;
            }
        }
        return null;
    }

    static boolean lockSingleInstance(Path runtime) {
        try {
            Files.createDirectories(runtime);
            FileChannel channel = FileChannel.open(runtime.resolve("panel.lock"),
                    StandardOpenOption.CREATE, StandardOpenOption.WRITE);
            FileLock lock = channel.tryLock();
            return lock != null; // held until the JVM exits
        } catch (IOException e) {
            return true; // cannot tell; do not block the user over it
        }
    }

    static void fatal(String message) {
        JOptionPane.showMessageDialog(null, message, TITLE, JOptionPane.ERROR_MESSAGE);
        System.exit(1);
    }

    static ThreadFactory daemon(String name) {
        return r -> {
            Thread t = new Thread(r, name);
            t.setDaemon(true);
            return t;
        };
    }

    static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    static boolean waitFor(BooleanSupplier check, long timeoutMs) {
        long end = System.currentTimeMillis() + timeoutMs;
        while (!check.getAsBoolean() && System.currentTimeMillis() < end) sleep(100);
        return check.getAsBoolean();
    }

    static boolean truthy(String value) {
        if (value == null) return false;
        String v = value.trim().toLowerCase(Locale.ROOT);
        return v.equals("1") || v.equals("true") || v.equals("yes");
    }

    // =================================================================== settings

    /** The panel's own preferences: ports, keep-running, auto-reload. */
    static final class Settings {
        private final Path file;
        private final Properties props = new Properties();

        Settings(Path file) {
            this.file = file;
            try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
                props.load(r);
            } catch (IOException ignored) {
                // No file yet: defaults.
            }
        }

        int port(String id, int fallback) {
            try {
                return Integer.parseInt(props.getProperty(id + ".port"));
            } catch (RuntimeException e) {
                return fallback;
            }
        }

        boolean flag(String key, boolean fallback) {
            String v = props.getProperty(key);
            return v == null ? fallback : Boolean.parseBoolean(v);
        }

        synchronized void put(String key, String value) {
            props.setProperty(key, value);
            try {
                Files.createDirectories(file.getParent());
                try (Writer w = Files.newBufferedWriter(file, StandardCharsets.UTF_8)) {
                    props.store(w, "Turbo EA control panel - local settings, not committed");
                }
            } catch (IOException ignored) {
                // Settings are a convenience; losing them is not fatal.
            }
        }
    }

    /**
     * backend/.env, edited in place: an existing KEY=value line is rewritten
     * where it stands, so comments and order survive; a new key is appended.
     */
    static final class EnvFile {
        static final Pattern LINE = Pattern.compile("^\\s*(?:export\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*=(.*)$");

        static final String TEMPLATE = String.join("\n",
                "# Local dev env for the Turbo EA backend, read by the control panel",
                "# (tools/control-panel). Local development only - not committed.",
                "",
                "POSTGRES_HOST=localhost",
                "POSTGRES_PORT=5432",
                "POSTGRES_DB=turboea",
                "POSTGRES_USER=turboea",
                "POSTGRES_PASSWORD=turboea",
                "",
                "ENVIRONMENT=development",
                "SECRET_KEY=local-dev-only-change-me",
                "ACCESS_TOKEN_EXPIRE_MINUTES=1440",
                "ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8000",
                "",
                "RESET_DB=false",
                "SEED_DEMO=true",
                "SEED_BPM=true",
                "SEED_PPM=true",
                "") ;

        final Path file;
        private final List<String> lines = new ArrayList<>();

        EnvFile(Path file) {
            this.file = file;
            reload();
        }

        synchronized boolean exists() {
            return Files.isRegularFile(file);
        }

        synchronized void reload() {
            lines.clear();
            try {
                lines.addAll(Files.readAllLines(file, StandardCharsets.UTF_8));
            } catch (IOException ignored) {
                // Missing: empty until saved.
            }
        }

        synchronized String text() {
            return lines.isEmpty() && !exists() ? TEMPLATE : String.join("\n", lines) + "\n";
        }

        synchronized void setText(String text) {
            lines.clear();
            for (String l : text.split("\\R", -1)) lines.add(l);
            while (!lines.isEmpty() && lines.get(lines.size() - 1).isEmpty()) lines.remove(lines.size() - 1);
        }

        /** Every KEY=value, later lines winning - the shape the backend's os.getenv sees. */
        synchronized Map<String, String> values() {
            Map<String, String> out = new LinkedHashMap<>();
            List<String> source = lines.isEmpty() && !exists() ? List.of(TEMPLATE.split("\n")) : lines;
            for (String l : source) {
                Matcher m = LINE.matcher(l);
                if (m.matches()) out.put(m.group(1), unquote(m.group(2)));
            }
            return out;
        }

        synchronized String get(String key) {
            return values().get(key);
        }

        synchronized void set(String key, String value) {
            if (lines.isEmpty() && !exists()) setText(TEMPLATE);
            String rendered = key + "=" + value;
            for (int i = lines.size() - 1; i >= 0; i--) {
                Matcher m = LINE.matcher(lines.get(i));
                if (m.matches() && m.group(1).equals(key)) {
                    lines.set(i, rendered);
                    return;
                }
            }
            if (value.isEmpty()) return; // nothing to add
            lines.add(rendered);
        }

        synchronized void save() throws IOException {
            Files.createDirectories(file.getParent());
            Files.writeString(file, String.join("\n", lines) + "\n", StandardCharsets.UTF_8);
        }

        static String unquote(String raw) {
            String v = raw.trim();
            if (v.length() >= 2 && (v.startsWith("\"") && v.endsWith("\"") || v.startsWith("'") && v.endsWith("'"))) {
                return v.substring(1, v.length() - 1);
            }
            int hash = v.indexOf(" #");
            return hash >= 0 ? v.substring(0, hash).trim() : v;
        }
    }

    // ====================================================================== ports

    record Owner(long pid, String name, String cmd) {}

    record PortOwner(String text, boolean ours, List<Long> pids) {}

    static final class Ports {
        static boolean open(int port) {
            // Vite binds "localhost", which may resolve to ::1 only.
            return probe("127.0.0.1", port) || probe("::1", port);
        }

        static boolean probe(String host, int port) {
            try (Socket s = new Socket()) {
                s.connect(new InetSocketAddress(host, port), 600);
                return true;
            } catch (IOException e) {
                return false;
            }
        }

        /** Who listens on a port. Empty when nobody, or when the platform will not say. */
        static List<Owner> owners(int port) {
            List<Owner> owners = new ArrayList<>();
            if (WINDOWS) {
                String script = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $t=[char]9;"
                        + " $ids=@(Get-NetTCPConnection -State Listen -LocalPort " + port
                        + " -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique);"
                        + " foreach($id in $ids){ $w=Get-CimInstance Win32_Process -Filter ('ProcessId='+$id) -ErrorAction SilentlyContinue;"
                        + " [string]$id + $t + [string]$w.Name + $t + [string]$w.CommandLine }";
                for (String line : run(List.of("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script)).split("\\R")) {
                    String[] parts = line.split("\t", 3);
                    if (parts.length < 1 || parts[0].isBlank()) continue;
                    try {
                        owners.add(new Owner(Long.parseLong(parts[0].trim()),
                                parts.length > 1 ? parts[1] : "", parts.length > 2 ? parts[2] : ""));
                    } catch (NumberFormatException ignored) {
                        // Not a result line.
                    }
                }
                return owners;
            }
            Owner current = null;
            for (String line : run(List.of("lsof", "-nP", "-iTCP:" + port, "-sTCP:LISTEN", "-Fpc")).split("\\R")) {
                if (line.startsWith("p")) {
                    long pid = Long.parseLong(line.substring(1).trim());
                    String cmd = ProcessHandle.of(pid).flatMap(h -> h.info().commandLine()).orElse("");
                    current = new Owner(pid, "", cmd);
                    owners.add(current);
                } else if (line.startsWith("c") && current != null) {
                    owners.set(owners.size() - 1, new Owner(current.pid(), line.substring(1), current.cmd()));
                }
            }
            return owners;
        }

        /**
         * A listener is Turbo EA's when its command line names this checkout
         * (the venv's python, vite.js under frontend/node_modules) or the
         * backend's ASGI app. Anything else - including a process we may not
         * inspect - belongs to someone else.
         */
        static boolean isOurs(String cmd, Path root) {
            if (cmd == null || cmd.isBlank()) return false;
            String folder = root.toString() + java.io.File.separator;
            boolean hasRoot = WINDOWS
                    ? cmd.toLowerCase(Locale.ROOT).contains(folder.toLowerCase(Locale.ROOT))
                    : cmd.contains(folder);
            return hasRoot || cmd.contains("app.main:app");
        }

        static String run(List<String> command) {
            try {
                Process p = new ProcessBuilder(command)
                        .redirectError(ProcessBuilder.Redirect.DISCARD)
                        .start();
                p.getOutputStream().close();
                byte[] out = p.getInputStream().readAllBytes();
                p.waitFor(10, TimeUnit.SECONDS);
                return new String(out, StandardCharsets.UTF_8);
            } catch (IOException e) {
                return "";
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return "";
            }
        }

        static void kill(long pid) {
            if (WINDOWS) {
                run(List.of("taskkill", "/PID", Long.toString(pid), "/T", "/F"));
            } else {
                ProcessHandle.of(pid).ifPresent(ProcessHandle::destroy);
            }
        }
    }

    // ======================================================================= logs

    enum Level { INFO, WARN, ERROR, PANEL }

    record LogLine(long time, String text, Level level) {}

    static final Pattern ANSI = Pattern.compile("\u001B\\[[0-9;?]*[A-Za-z]");
    static final Pattern ERROR_LINE = Pattern.compile(
            "\\b(ERROR|FATAL|CRITICAL)\\b|^Traceback|^\\s*\\w*(Error|Exception):|\\[X\\]|✘|\\berror TS\\d+");
    static final Pattern WARN_LINE = Pattern.compile("\\bWARN(ING)?\\b|▲");

    static final Pattern URL = Pattern.compile("https?://[^\\s\"'<>()\\[\\]]+");
    static final String LINK_ATTR = "panel-link";

    static Level levelOf(String text) {
        if (ERROR_LINE.matcher(text).find()) return Level.ERROR;
        if (WARN_LINE.matcher(text).find()) return Level.WARN;
        return Level.INFO;
    }

    // ======================================================================= apps

    enum Tone { IDLE, BUSY, OK, BAD }

    enum State {
        STOPPED("Stopped", Tone.IDLE),
        STARTING("Starting", Tone.BUSY),
        RUNNING("Running", Tone.OK),
        STOPPING("Stopping", Tone.BUSY),
        RESTARTING("Restarting", Tone.BUSY),
        CRASHED("Crashed", Tone.BAD),
        FAILED("Failed", Tone.BAD),
        BLOCKED("Port busy", Tone.BAD);

        final String label;
        final Tone tone;

        State(String label, Tone tone) {
            this.label = label;
            this.tone = tone;
        }

        boolean idle() {
            return this == STOPPED || this == CRASHED || this == FAILED || this == BLOCKED;
        }
    }

    abstract static class ManagedApp {
        final String id;
        final String label;
        final String subtitle;
        final Path root;
        final Path cwd;
        final Settings settings;

        // Starting is serialised on this thread. Stopping deliberately is not:
        // it must be able to interrupt a start that is still preparing.
        final ExecutorService worker;

        volatile State state = State.STOPPED;
        volatile String message = "";
        volatile Process process;
        volatile long startedAt;
        volatile boolean preparing;
        volatile boolean wantRunning;
        volatile boolean stopping;
        volatile PortOwner owner;
        volatile int port;
        volatile boolean keepRunning;
        int crashStreak;
        long ownerCheckedAt;
        ScheduledFuture<?> restartTask;

        private final List<LogLine> logs = new ArrayList<>();
        final ConcurrentLinkedQueue<LogLine> pending = new ConcurrentLinkedQueue<>();
        final List<Runnable> listeners = new CopyOnWriteArrayList<>();
        volatile boolean cleared;

        ManagedApp(String id, String label, String subtitle, Path root, Path cwd, Settings settings, int defaultPort) {
            this.id = id;
            this.label = label;
            this.subtitle = subtitle;
            this.root = root;
            this.cwd = cwd;
            this.settings = settings;
            this.port = settings.port(id, defaultPort);
            this.keepRunning = settings.flag(id + ".keepRunning", false);
            this.worker = Executors.newSingleThreadExecutor(daemon("panel-" + id));
        }

        /** Work before launch, such as npm install. Return false to fail the start. */
        boolean prepare(boolean fromRestart) throws Exception {
            return true;
        }

        abstract List<String> command();

        void environment(Map<String, String> env) {}

        String url() {
            return "http://localhost:" + port;
        }

        /** The app's base address, shown as a link in the header. */
        String address() {
            return "http://localhost:" + port;
        }

        String runningMessage() {
            return "";
        }

        // ------------------------------------------------------------- state

        void setState(State next, String text) {
            state = next;
            message = text == null ? "" : text;
            fire();
        }

        void fire() {
            listeners.forEach(Runnable::run);
        }

        void log(String text, Level level) {
            for (String raw : text.split("\\R")) {
                String line = ANSI.matcher(raw).replaceAll("").replace("\r", "");
                if (line.isBlank()) continue;
                LogLine entry = new LogLine(System.currentTimeMillis(), line, level != null ? level : levelOf(line));
                synchronized (logs) {
                    logs.add(entry);
                    if (logs.size() > LOG_LIMIT) logs.subList(0, logs.size() - LOG_LIMIT).clear();
                }
                pending.add(entry);
            }
        }

        void note(String text, Level level) {
            log("[panel] " + text, level);
        }

        List<LogLine> logSnapshot() {
            synchronized (logs) {
                return new ArrayList<>(logs);
            }
        }

        void clearLogs() {
            synchronized (logs) {
                logs.clear();
            }
            pending.clear();
            cleared = true;
        }

        // ------------------------------------------------------- user actions

        void requestStart() {
            worker.submit(() -> doStart(false));
        }

        void requestStop() {
            ASYNC.submit(this::doStop);
        }

        void requestRestart() {
            ASYNC.submit(() -> {
                doStop();
                waitFor(() -> !preparing, 15_000);
                worker.submit(() -> doStart(false));
            });
        }

        /** Null when saved, otherwise the reason it was refused. */
        String changePort(int next, List<ManagedApp> all) {
            if (next == port) return null;
            if (process != null || preparing || !state.idle()) return "Stop the " + label + " before changing its port.";
            if (next < 1024 || next > 65535) return "Port must be a whole number between 1024 and 65535.";
            for (ManagedApp other : all) {
                if (other != this && other.port == next) return "Port " + next + " is already set for the " + other.label + ".";
            }
            port = next;
            owner = null;
            ownerCheckedAt = 0;
            settings.put(id + ".port", Integer.toString(port));
            if (state == State.BLOCKED) setState(State.STOPPED, "");
            else fire();
            return null;
        }

        void changeKeepRunning(boolean value) {
            keepRunning = value;
            settings.put(id + ".keepRunning", Boolean.toString(value));
            fire();
        }

        /** Stops a leftover Turbo EA process on our port. Null when done, else why not. */
        String freePort() {
            refreshOwner(true);
            PortOwner o = owner;
            if (o == null || o.pids().isEmpty()) return null;
            if (!o.ours()) return "Port " + port + " belongs to " + o.text() + ". The panel will not stop another app.";
            o.pids().forEach(Ports::kill);
            note("stopped the leftover Turbo EA process on port " + port, Level.PANEL);
            sleep(1500);
            owner = null;
            setState(State.STOPPED, "");
            return null;
        }

        // --------------------------------------------------------- lifecycle

        void doStart(boolean fromRestart) {
            if (process != null || state == State.STARTING || state == State.STOPPING) return;
            cancelRestart();

            if (Ports.open(port)) {
                refreshOwner(true);
                String who = owner != null ? owner.text() : "another program";
                wantRunning = false;
                note("not started: port " + port + " is in use by " + who, Level.WARN);
                setState(State.BLOCKED, "Port " + port + " is in use by " + who + ".");
                return;
            }

            owner = null;
            wantRunning = true;
            stopping = false;
            if (!fromRestart) crashStreak = 0;
            setState(State.STARTING, "Preparing" + ELLIPSIS);

            preparing = true;
            boolean ok;
            try {
                ok = prepare(fromRestart);
            } catch (Exception e) {
                note(String.valueOf(e.getMessage()), Level.ERROR);
                ok = false;
            }
            preparing = false;

            if (!wantRunning) {
                stopping = false;
                setState(State.STOPPED, "");
                return;
            }
            if (!ok) {
                wantRunning = false;
                if (state == State.STARTING) setState(State.FAILED, "Preparation failed - see the log.");
                return;
            }
            launch();
        }

        void launch() {
            List<String> cmd = command();
            note(String.join(" ", cmd) + "   (port " + port + ")", Level.PANEL);
            ProcessBuilder pb = new ProcessBuilder(cmd).directory(cwd.toFile()).redirectErrorStream(true);
            environment(pb.environment());
            Process p;
            try {
                p = pb.start();
            } catch (IOException e) {
                wantRunning = false;
                note("could not start: " + e.getMessage(), Level.ERROR);
                setState(State.FAILED, "Could not start: " + e.getMessage());
                return;
            }
            process = p;
            startedAt = System.currentTimeMillis();
            setState(State.STARTING, "Waiting for port " + port + ELLIPSIS);
            pump(p);
            p.onExit().thenRun(() -> worker.submit(() -> onExit(p)));
        }

        /** A preparation step that Stop can interrupt. Returns the exit code. */
        int runStep(List<String> cmd) throws IOException, InterruptedException {
            note(String.join(" ", cmd), Level.PANEL);
            ProcessBuilder pb = new ProcessBuilder(cmd).directory(cwd.toFile()).redirectErrorStream(true);
            pb.environment().put("PYTHONUNBUFFERED", "1");
            Process p = pb.start();
            process = p;
            Thread reader = pump(p);
            int code = p.waitFor();
            reader.join(2000);
            process = null;
            return code;
        }

        Thread pump(Process p) {
            try {
                p.getOutputStream().close(); // no prompts: nothing will ever answer them
            } catch (IOException ignored) {
                // Already closed.
            }
            Thread t = new Thread(() -> {
                try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = r.readLine()) != null) log(line, null);
                } catch (IOException ignored) {
                    // Stream closed when the process ended.
                }
            }, "panel-" + id + "-output");
            t.setDaemon(true);
            t.start();
            return t;
        }

        void onExit(Process p) {
            if (process != p) return;
            int code = p.exitValue();
            long uptime = System.currentTimeMillis() - startedAt;
            process = null;
            startedAt = 0;

            if (stopping || !wantRunning) {
                stopping = false;
                note("stopped", Level.PANEL);
                setState(State.STOPPED, "");
                return;
            }

            note("exited unexpectedly (code " + code + ")", Level.ERROR);
            if (uptime > STABLE_UPTIME_MS) crashStreak = 0;
            crashStreak++;

            if (!keepRunning) {
                wantRunning = false;
                setState(State.CRASHED, "Exited with code " + code + ".");
                return;
            }
            if (crashStreak > MAX_CRASH_STREAK) {
                wantRunning = false;
                setState(State.CRASHED, "Crashed " + crashStreak + " times in a row - keep running gave up. Check the log.");
                return;
            }
            long delay = Math.min(30_000, 2_000L << (crashStreak - 1));
            note("keep running: restarting in " + delay / 1000 + "s (attempt " + crashStreak + ")", Level.WARN);
            setState(State.RESTARTING, "Crashed (code " + code + "). Restarting in " + delay / 1000 + "s" + ELLIPSIS);
            restartTask = TIMER.schedule(() -> worker.submit(() -> {
                restartTask = null;
                if (wantRunning) doStart(true);
            }), delay, TimeUnit.MILLISECONDS);
        }

        void doStop() {
            wantRunning = false;
            cancelRestart();
            Process p = process;
            if (p == null) {
                if (!preparing && state != State.STOPPED) setState(State.STOPPED, "");
                return;
            }
            stopping = true;
            setState(State.STOPPING, "Stopping" + ELLIPSIS);
            killTree(p);
            waitFor(() -> process == null, 15_000);
        }

        void cancelRestart() {
            ScheduledFuture<?> task = restartTask;
            if (task != null) task.cancel(false);
            restartTask = null;
        }

        /** For the shutdown hook: no waiting on other threads. */
        void killNow() {
            wantRunning = false;
            stopping = true;
            Process p = process;
            if (p != null) killTree(p);
        }

        static void killTree(Process p) {
            if (WINDOWS) {
                // taskkill takes the whole tree: uvicorn's reloader -> worker, or node -> esbuild.
                Ports.run(List.of("taskkill", "/PID", Long.toString(p.pid()), "/T", "/F"));
                p.destroyForcibly();
                return;
            }
            p.descendants().forEach(ProcessHandle::destroy);
            p.destroy();
            TIMER.schedule(() -> {
                p.descendants().forEach(ProcessHandle::destroyForcibly);
                p.destroyForcibly();
            }, 8, TimeUnit.SECONDS);
        }

        // ---------------------------------------------------------- polling

        /** Marks a start as running once its port answers; keeps the port-owner note fresh. */
        void poll() {
            boolean open = Ports.open(port);
            if (process != null) {
                if (open && state == State.STARTING && !preparing) {
                    note("listening on port " + port, Level.PANEL);
                    setState(State.RUNNING, runningMessage());
                }
                return;
            }
            if (preparing || !state.idle()) return;
            PortOwner before = owner;
            if (open) refreshOwner(false);
            else owner = null;
            if (state == State.BLOCKED && !open) setState(State.STOPPED, "");
            else if (!Objects.equals(before, owner)) fire();
        }

        void refreshOwner(boolean force) {
            long now = System.currentTimeMillis();
            if (!force && now - ownerCheckedAt < 10_000) return;
            ownerCheckedAt = now;
            List<Owner> found = Ports.owners(port);
            if (found.isEmpty()) {
                owner = new PortOwner("another program (could not identify it)", false, List.of());
                return;
            }
            boolean ours = found.stream().allMatch(o -> Ports.isOurs(o.cmd(), root));
            StringBuilder names = new StringBuilder();
            List<Long> pids = new ArrayList<>();
            for (Owner o : found) {
                if (names.length() > 0) names.append(", ");
                names.append(o.name().isBlank() ? "process" : o.name()).append(" (PID ").append(o.pid()).append(')');
                pids.add(o.pid());
            }
            owner = new PortOwner(ours ? names + " - a Turbo EA process this panel did not start" : names.toString(), ours, pids);
        }
    }

    static final class BackendApp extends ManagedApp {
        final EnvFile env;
        volatile boolean reload;

        BackendApp(Path root, Settings settings, EnvFile env) {
            super("backend", "Backend", "FastAPI · uvicorn · settings from backend/.env",
                    root, root.resolve("backend"), settings, 8000);
            this.env = env;
            this.reload = settings.flag("backend.reload", true);
        }

        void changeReload(boolean value) {
            reload = value;
            settings.put("backend.reload", Boolean.toString(value));
            fire();
        }

        Path venvPython() {
            Path venv = cwd.resolve(".venv");
            return WINDOWS ? venv.resolve("Scripts").resolve("python.exe") : venv.resolve("bin").resolve("python");
        }

        @Override
        boolean prepare(boolean fromRestart) throws Exception {
            env.reload();
            if (!env.exists()) {
                note("backend/.env not found - using the built-in defaults. Open Settings to create it.", Level.WARN);
            }

            if (!Files.isRegularFile(venvPython())) {
                setState(State.STARTING, "Creating backend/.venv and installing dependencies (first run, a few minutes)" + ELLIPSIS);
                int code = runStep(List.of(WINDOWS ? "python" : "python3", "-m", "venv", ".venv"));
                if (code != 0 || !wantRunning) return false;
                code = runStep(List.of(venvPython().toString(), "-m", "pip", "install", "-e", ".[dev]"));
                if (code != 0) return false;
            }

            Map<String, String> vars = env.values();
            String host = vars.getOrDefault("POSTGRES_HOST", "localhost");
            int dbPort;
            try {
                dbPort = Integer.parseInt(vars.getOrDefault("POSTGRES_PORT", "5432").trim());
            } catch (NumberFormatException e) {
                note("POSTGRES_PORT is not a number - fix it in Settings.", Level.ERROR);
                return false;
            }
            if (!Ports.probe(host, dbPort)) {
                note("PostgreSQL is not reachable at " + host + ":" + dbPort
                        + ". Start it, or change the database in Settings.", Level.ERROR);
                setState(State.FAILED, "PostgreSQL is not reachable at " + host + ":" + dbPort + ".");
                return false;
            }

            if (truthy(vars.get("RESET_DB"))) {
                if (fromRestart) {
                    note("keep running will not restart with RESET_DB=true - that would wipe the database again.", Level.ERROR);
                    setState(State.FAILED, "Not restarted: RESET_DB is on.");
                    return false;
                }
                AtomicBoolean go = new AtomicBoolean(false);
                SwingUtilities.invokeAndWait(() -> go.set(JOptionPane.showConfirmDialog(null,
                        "RESET_DB is on in backend/.env.\n\nThis start DROPS EVERY TABLE in "
                                + vars.getOrDefault("POSTGRES_DB", "turboea") + " and re-seeds it.\nContinue?",
                        "Reset the database?", JOptionPane.OK_CANCEL_OPTION, JOptionPane.WARNING_MESSAGE)
                        == JOptionPane.OK_OPTION));
                if (!go.get()) {
                    note("start cancelled: RESET_DB is on", Level.WARN);
                    wantRunning = false;
                    return true; // doStart sees wantRunning=false and settles on Stopped
                }
            }
            return true;
        }

        @Override
        List<String> command() {
            List<String> cmd = new ArrayList<>(List.of(venvPython().toString(), "-m", "uvicorn", "app.main:app",
                    "--host", "127.0.0.1", "--port", Integer.toString(port)));
            if (reload) cmd.add("--reload");
            return cmd;
        }

        @Override
        void environment(Map<String, String> vars) {
            vars.putAll(env.values());
            vars.put("PYTHONUNBUFFERED", "1");
            vars.put("PYTHONIOENCODING", "utf-8");
        }

        @Override
        String url() {
            return "http://localhost:" + port + "/api/docs";
        }

        @Override
        String runningMessage() {
            return "API docs at /api/docs (development mode). Demo seeding may still be running.";
        }
    }

    static final class FrontendApp extends ManagedApp {
        private final BackendApp backend;

        FrontendApp(Path root, Settings settings, BackendApp backend) {
            super("frontend", "Frontend", "Vite dev server · proxies /api to the backend",
                    root, root.resolve("frontend"), settings, 5173);
            this.backend = backend;
        }

        Path vite() {
            return cwd.resolve("node_modules").resolve("vite").resolve("bin").resolve("vite.js");
        }

        @Override
        boolean prepare(boolean fromRestart) throws Exception {
            if (!Files.isRegularFile(vite())) {
                setState(State.STARTING, "Installing dependencies (first run, a few minutes)" + ELLIPSIS);
                int code = runStep(WINDOWS ? List.of("cmd.exe", "/d", "/c", "npm", "install") : List.of("npm", "install"));
                if (code != 0) return false;
            }
            return true;
        }

        @Override
        List<String> command() {
            return List.of("node", vite().toString(), "--port", Integer.toString(port), "--strictPort");
        }

        @Override
        void environment(Map<String, String> env) {
            // Read by vite.config.ts; the committed default is http://localhost:8000.
            env.put("TURBO_EA_API_TARGET", "http://127.0.0.1:" + backend.port); // the backend binds 127.0.0.1
            env.put("BROWSER", "none");
            env.put("FORCE_COLOR", "0");
            env.put("NO_COLOR", "1");
        }

        @Override
        String runningMessage() {
            return "The first user to register becomes admin.";
        }
    }

    // ========================================================================= UI

    static final Color OK = new Color(0x1A8A4A);
    static final Color BUSY = new Color(0xB07000);
    static final Color BAD = new Color(0xC53030);
    static final Color IDLE = new Color(0x677184);
    static final Color LOG_BG = new Color(0x12151C);
    static final Color LOG_TEXT = new Color(0xD6DBE4);
    static final Color LOG_MUTED = new Color(0x6F7A8E);
    static final Color LOG_WARN = new Color(0xF0B545);
    static final Color LOG_ERROR = new Color(0xFF7B7B);
    static final Color LOG_PANEL = new Color(0x7FB0FF);

    static Color toneColor(Tone tone) {
        switch (tone) {
            case OK: return OK;
            case BUSY: return BUSY;
            case BAD: return BAD;
            default: return IDLE;
        }
    }

    static Font monoFont() {
        String[] preferred = {"Cascadia Mono", "Consolas", "JetBrains Mono", "Menlo", "SF Mono", "DejaVu Sans Mono"};
        List<String> available = List.of(GraphicsEnvironment.getLocalGraphicsEnvironment().getAvailableFontFamilyNames());
        for (String name : preferred) if (available.contains(name)) return new Font(name, Font.PLAIN, 12);
        return new Font(Font.MONOSPACED, Font.PLAIN, 12);
    }

    static void openBrowser(String url) {
        try {
            if (Desktop.isDesktopSupported() && Desktop.getDesktop().isSupported(Desktop.Action.BROWSE)) {
                Desktop.getDesktop().browse(new URI(url));
                return;
            }
            if (WINDOWS) new ProcessBuilder("rundll32", "url.dll,FileProtocolHandler", url).start();
            else new ProcessBuilder("xdg-open", url).start();
        } catch (Exception e) {
            JOptionPane.showMessageDialog(null, "Could not open a browser. Go to " + url, "Open", JOptionPane.WARNING_MESSAGE);
        }
    }

    static Image appIcon() {
        BufferedImage img = new BufferedImage(64, 64, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = img.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.setColor(new Color(0x0F7EB5));
        g.fillRoundRect(0, 0, 64, 64, 16, 16);
        g.setColor(Color.WHITE);
        g.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 26));
        FontMetrics fm = g.getFontMetrics();
        String text = "EA";
        g.drawString(text, (64 - fm.stringWidth(text)) / 2, (64 - fm.getHeight()) / 2 + fm.getAscent());
        g.dispose();
        return img;
    }

    static final class MainWindow extends JFrame {
        private final List<ManagedApp> apps;
        private final JButton settingsButton = new JButton("Settings" + ELLIPSIS);
        private final JButton startAll = new JButton("Start both");
        private final JButton stopAll = new JButton("Stop both");

        MainWindow(Path root, List<ManagedApp> apps, EnvFile env, BackendApp backend) {
            super(TITLE);
            this.apps = apps;
            setIconImage(appIcon());
            setDefaultCloseOperation(WindowConstants.DO_NOTHING_ON_CLOSE);

            JPanel bar = new JPanel(new BorderLayout());
            bar.setBorder(new EmptyBorder(10, 14, 10, 14));
            JLabel title = new JLabel(TITLE);
            title.setFont(title.getFont().deriveFont(Font.BOLD, 15f));
            JLabel where = new JLabel("   " + root);
            where.setForeground(IDLE);
            JPanel left = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
            left.setOpaque(false);
            left.add(title);
            left.add(where);
            JPanel right = new JPanel(new FlowLayout(FlowLayout.RIGHT, 6, 0));
            right.setOpaque(false);
            right.add(settingsButton);
            right.add(startAll);
            right.add(stopAll);
            bar.add(left, BorderLayout.WEST);
            bar.add(right, BorderLayout.EAST);

            settingsButton.addActionListener(e -> new SettingsDialog(this, env, backend).setVisible(true));
            startAll.addActionListener(e -> apps.forEach(ManagedApp::requestStart));
            stopAll.addActionListener(e -> apps.forEach(ManagedApp::requestStop));

            List<AppPanel> panels = new ArrayList<>();
            for (ManagedApp app : apps) panels.add(new AppPanel(app, apps));
            JSplitPane split = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, panels.get(0), panels.get(1));
            split.setResizeWeight(0.5);
            split.setBorder(new EmptyBorder(0, 8, 8, 8));
            split.setContinuousLayout(true);

            getContentPane().setLayout(new BorderLayout());
            getContentPane().add(bar, BorderLayout.NORTH);
            getContentPane().add(split, BorderLayout.CENTER);

            for (ManagedApp app : apps) app.listeners.add(() -> SwingUtilities.invokeLater(this::refreshBar));
            refreshBar();

            addWindowListener(new WindowAdapter() {
                @Override
                public void windowClosing(WindowEvent e) {
                    closeRequested();
                }
            });

            setSize(1440, 860);
            setMinimumSize(new Dimension(900, 520));
            setLocationRelativeTo(null);
            SwingUtilities.invokeLater(() -> split.setDividerLocation(0.5));
        }

        private void refreshBar() {
            startAll.setEnabled(apps.stream().anyMatch(a -> a.state.idle()));
            stopAll.setEnabled(apps.stream().anyMatch(a -> !a.state.idle()));
        }

        private void closeRequested() {
            boolean anyActive = apps.stream().anyMatch(a -> !a.state.idle() || a.process != null);
            if (anyActive) {
                int choice = JOptionPane.showConfirmDialog(this,
                        "Closing the control panel stops the backend and the frontend.",
                        "Stop both and close?", JOptionPane.OK_CANCEL_OPTION, JOptionPane.WARNING_MESSAGE);
                if (choice != JOptionPane.OK_OPTION) return;
            }
            setTitle(TITLE + " - stopping" + ELLIPSIS);
            setEnabled(false);
            ASYNC.submit(() -> {
                List<CompletableFuture<Void>> stops = new ArrayList<>();
                for (ManagedApp app : apps) stops.add(CompletableFuture.runAsync(app::doStop, ASYNC));
                try {
                    CompletableFuture.allOf(stops.toArray(new CompletableFuture[0])).get(20, TimeUnit.SECONDS);
                } catch (Exception ignored) {
                    // The shutdown hook kills whatever is left.
                }
                System.exit(0);
            });
        }
    }

    /** Edits backend/.env: a form for the common keys, plus the raw file. */
    static final class SettingsDialog extends JDialog {
        enum Kind { TEXT, SECRET, FLAG, CHOICE }

        record Field(String key, String label, Kind kind, String hint, String... choices) {}

        static final Object[][] GROUPS = {
                {"Database (PostgreSQL)", new Field[]{
                        new Field("POSTGRES_HOST", "Host", Kind.TEXT, "localhost"),
                        new Field("POSTGRES_PORT", "Port", Kind.TEXT, "5432"),
                        new Field("POSTGRES_DB", "Database", Kind.TEXT, "turboea"),
                        new Field("POSTGRES_USER", "User", Kind.TEXT, "turboea"),
                        new Field("POSTGRES_PASSWORD", "Password", Kind.SECRET, ""),
                }},
                {"Startup data", new Field[]{
                        new Field("SEED_DEMO", "Seed NexaTech demo data", Kind.FLAG, ""),
                        new Field("SEED_BPM", "Seed demo BPM processes", Kind.FLAG, ""),
                        new Field("SEED_PPM", "Seed demo PPM data", Kind.FLAG, ""),
                        new Field("SEED_SECURITY", "Seed demo compliance findings", Kind.FLAG, ""),
                        new Field("SEED_NORA", "Seed NORA content", Kind.FLAG, ""),
                        new Field("RESET_DB", "RESET_DB - drop every table on start", Kind.FLAG, ""),
                }},
                {"Server", new Field[]{
                        new Field("ENVIRONMENT", "Environment", Kind.CHOICE, "", "development", "production"),
                        new Field("SECRET_KEY", "Secret key", Kind.SECRET, ""),
                        new Field("ACCESS_TOKEN_EXPIRE_MINUTES", "Session length (minutes)", Kind.TEXT, "1440"),
                        new Field("ALLOWED_ORIGINS", "Allowed origins (CORS)", Kind.TEXT, "comma-separated"),
                }},
                {"AI suggestions", new Field[]{
                        new Field("AI_PROVIDER_URL", "Provider URL", Kind.TEXT, "e.g. http://localhost:11434"),
                        new Field("AI_MODEL", "Model", Kind.TEXT, "e.g. gemma3:4b"),
                        new Field("AI_SEARCH_PROVIDER", "Search provider", Kind.CHOICE, "", "", "duckduckgo", "google", "searxng"),
                        new Field("AI_AUTO_CONFIGURE", "Auto-configure AI on startup", Kind.FLAG, ""),
                }},
                {"Email (SMTP)", new Field[]{
                        new Field("SMTP_HOST", "Host", Kind.TEXT, "empty = email off"),
                        new Field("SMTP_PORT", "Port", Kind.TEXT, "587"),
                        new Field("SMTP_USER", "User", Kind.TEXT, ""),
                        new Field("SMTP_PASSWORD", "Password", Kind.SECRET, ""),
                        new Field("SMTP_FROM", "From address", Kind.TEXT, "noreply@turboea.local"),
                        new Field("SMTP_TLS", "Use TLS", Kind.FLAG, ""),
                }},
        };

        private final EnvFile env;
        private final BackendApp backend;
        private final Map<String, JComponent> inputs = new LinkedHashMap<>();
        private final JTextArea raw = new JTextArea();
        private final JTabbedPane tabs = new JTabbedPane();
        private int shownTab;

        SettingsDialog(Frame owner, EnvFile env, BackendApp backend) {
            super(owner, "Settings - backend/.env", true);
            this.env = env;
            this.backend = backend;
            env.reload();

            JPanel form = new JPanel();
            form.setLayout(new BoxLayout(form, BoxLayout.Y_AXIS));
            form.setBorder(new EmptyBorder(8, 12, 8, 12));
            for (Object[] group : GROUPS) form.add(buildGroup((String) group[0], (Field[]) group[1]));
            form.add(Box.createVerticalGlue());
            JScrollPane formScroll = new JScrollPane(form);
            formScroll.setBorder(BorderFactory.createEmptyBorder());
            formScroll.getVerticalScrollBar().setUnitIncrement(16);

            raw.setFont(monoFont());
            raw.setTabSize(4);
            JPanel rawBox = new JPanel(new BorderLayout());
            JLabel rawHint = new JLabel("Every KEY=value line is passed to the backend as an environment variable.");
            rawHint.setForeground(IDLE);
            rawHint.setBorder(new EmptyBorder(6, 8, 6, 8));
            rawBox.add(rawHint, BorderLayout.NORTH);
            rawBox.add(new JScrollPane(raw), BorderLayout.CENTER);

            tabs.addTab("Common", formScroll);
            tabs.addTab("Raw .env", rawBox);
            tabs.addChangeListener(e -> switchTab());
            loadForm();

            JLabel file = new JLabel(env.file.toString() + (env.exists() ? "" : "   (not created yet - Save creates it)"));
            file.setForeground(IDLE);
            JButton save = new JButton("Save");
            JButton cancel = new JButton("Cancel");
            save.addActionListener(e -> save());
            cancel.addActionListener(e -> dispose());
            JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT, 6, 0));
            buttons.add(save);
            buttons.add(cancel);
            JPanel foot = new JPanel(new BorderLayout());
            foot.setBorder(new EmptyBorder(8, 12, 10, 12));
            foot.add(file, BorderLayout.WEST);
            foot.add(buttons, BorderLayout.EAST);

            getContentPane().setLayout(new BorderLayout());
            getContentPane().add(tabs, BorderLayout.CENTER);
            getContentPane().add(foot, BorderLayout.SOUTH);
            getRootPane().setDefaultButton(save);
            setSize(720, 760);
            setLocationRelativeTo(owner);
        }

        private JComponent buildGroup(String title, Field[] fields) {
            JPanel box = new JPanel(new GridBagLayout());
            box.setBorder(BorderFactory.createCompoundBorder(
                    BorderFactory.createTitledBorder(title), new EmptyBorder(4, 8, 6, 8)));
            box.setAlignmentX(Component.LEFT_ALIGNMENT);
            GridBagConstraints c = new GridBagConstraints();
            c.insets = new Insets(3, 2, 3, 6);
            c.anchor = GridBagConstraints.WEST;
            int row = 0;
            for (Field f : fields) {
                JComponent input;
                c.gridy = row++;
                if (f.kind() == Kind.FLAG) {
                    JCheckBox box2 = new JCheckBox(f.label());
                    box2.setToolTipText(f.key());
                    if (f.key().equals("RESET_DB")) {
                        box2.setForeground(BAD);
                        box2.addActionListener(e -> {
                            if (box2.isSelected() && JOptionPane.showConfirmDialog(this,
                                    "With RESET_DB on, every backend start drops all tables and re-seeds.\n"
                                            + "Turn it off again after one start. Enable it?",
                                    "RESET_DB", JOptionPane.OK_CANCEL_OPTION, JOptionPane.WARNING_MESSAGE)
                                    != JOptionPane.OK_OPTION) {
                                box2.setSelected(false);
                            }
                        });
                    }
                    input = box2;
                    c.gridx = 0;
                    c.gridwidth = 2;
                    c.fill = GridBagConstraints.NONE;
                    c.weightx = 0;
                    box.add(input, c);
                    c.gridwidth = 1;
                } else {
                    JLabel label = new JLabel(f.label());
                    label.setToolTipText(f.key());
                    c.gridx = 0;
                    c.fill = GridBagConstraints.NONE;
                    c.weightx = 0;
                    box.add(label, c);
                    if (f.kind() == Kind.CHOICE) {
                        JComboBox<String> combo = new JComboBox<>(f.choices());
                        combo.setEditable(true);
                        input = combo;
                    } else if (f.kind() == Kind.SECRET) {
                        input = new JPasswordField(28);
                    } else {
                        JTextField text = new JTextField(28);
                        if (!f.hint().isEmpty()) text.setToolTipText(f.key() + " - " + f.hint());
                        input = text;
                    }
                    c.gridx = 1;
                    c.fill = GridBagConstraints.HORIZONTAL;
                    c.weightx = 1;
                    box.add(input, c);
                }
                if (input.getToolTipText() == null) input.setToolTipText(f.key());
                inputs.put(f.key(), input);
            }
            box.setMaximumSize(new Dimension(Integer.MAX_VALUE, box.getPreferredSize().height));
            return box;
        }

        private void loadForm() {
            Map<String, String> v = env.values();
            for (Map.Entry<String, JComponent> e : inputs.entrySet()) {
                String value = v.getOrDefault(e.getKey(), "");
                JComponent input = e.getValue();
                if (input instanceof JCheckBox box) box.setSelected(truthy(value));
                else if (input instanceof JComboBox<?> combo) combo.setSelectedItem(value);
                else if (input instanceof JTextField text) text.setText(value);
            }
            raw.setText(env.text());
            raw.setCaretPosition(0);
        }

        /** Writes the form into the env model. Flags and present keys only, so untouched blanks add nothing. */
        private void applyForm() {
            Map<String, String> before = env.values();
            for (Map.Entry<String, JComponent> e : inputs.entrySet()) {
                JComponent input = e.getValue();
                String value;
                if (input instanceof JCheckBox box) {
                    if (!box.isSelected() && !before.containsKey(e.getKey())) continue;
                    value = Boolean.toString(box.isSelected());
                } else if (input instanceof JComboBox<?> combo) {
                    value = Objects.toString(combo.getSelectedItem(), "").trim();
                } else {
                    value = ((JTextField) input).getText().trim();
                }
                if (value.equals(before.getOrDefault(e.getKey(), ""))) continue;
                env.set(e.getKey(), value);
            }
        }

        private void switchTab() {
            int next = tabs.getSelectedIndex();
            if (next == shownTab) return;
            if (shownTab == 0) {
                applyForm();
                raw.setText(env.text());
                raw.setCaretPosition(0);
            } else {
                env.setText(raw.getText());
                loadForm();
            }
            shownTab = next;
        }

        private void save() {
            if (tabs.getSelectedIndex() == 0) applyForm();
            else env.setText(raw.getText());
            try {
                env.save();
            } catch (IOException ex) {
                JOptionPane.showMessageDialog(this, "Could not save " + env.file + ":\n" + ex.getMessage(),
                        "Settings", JOptionPane.ERROR_MESSAGE);
                return;
            }
            dispose();
            if (backend.process != null) {
                int choice = JOptionPane.showConfirmDialog(getOwner(),
                        "Saved. The backend reads these settings when it starts.\nRestart the backend now?",
                        "Settings", JOptionPane.YES_NO_OPTION, JOptionPane.QUESTION_MESSAGE);
                if (choice == JOptionPane.YES_OPTION) backend.requestRestart();
            }
        }
    }

    static final class AppPanel extends JPanel {
        private final ManagedApp app;
        private final List<ManagedApp> all;

        private final JLabel status = new JLabel();
        private final JLabel facts = new JLabel();
        private final JLabel address = new JLabel();
        private final JLabel message = new JLabel();
        private final JButton freePort = new JButton("Stop it");
        private final JButton start = new JButton("Start");
        private final JButton stop = new JButton("Stop");
        private final JButton restart = new JButton("Restart");
        private final JButton open = new JButton("Open in browser");
        private final JTextField portField = new JTextField(6);
        private final JCheckBox keep = new JCheckBox("Keep running");
        private final JCheckBox reload = new JCheckBox("Auto-reload on code change");
        private final JTextField filter = new JTextField(16);
        private final JCheckBox problems = new JCheckBox("Errors & warnings");
        private final JCheckBox follow = new JCheckBox("Follow", true);
        private final JTextPane log = new JTextPane();
        private int docLines;

        private final SimpleAttributeSet timeStyle = style(LOG_MUTED, false);
        private final SimpleAttributeSet infoStyle = style(LOG_TEXT, false);
        private final SimpleAttributeSet warnStyle = style(LOG_WARN, false);
        private final SimpleAttributeSet errorStyle = style(LOG_ERROR, false);
        private final SimpleAttributeSet panelStyle = style(LOG_PANEL, true);
        private final Color linkColor = new Color(0x6FC3FF);
        private final SimpleDateFormat clock = new SimpleDateFormat("HH:mm:ss");

        AppPanel(ManagedApp app, List<ManagedApp> all) {
            super(new BorderLayout());
            this.app = app;
            this.all = all;
            setBorder(BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(new Color(0xDFE2E7)), new EmptyBorder(0, 0, 0, 0)));

            add(buildHeader(), BorderLayout.NORTH);
            add(buildLog(), BorderLayout.CENTER);

            start.addActionListener(e -> { start.setEnabled(false); app.requestStart(); });
            stop.addActionListener(e -> { stop.setEnabled(false); app.requestStop(); });
            restart.addActionListener(e -> { restart.setEnabled(false); app.requestRestart(); });
            open.addActionListener(e -> openBrowser(app.url()));
            freePort.addActionListener(e -> ASYNC.submit(() -> {
                String problem = app.freePort();
                if (problem != null) SwingUtilities.invokeLater(() -> warn(problem));
            }));
            keep.addActionListener(e -> app.changeKeepRunning(keep.isSelected()));
            reload.addActionListener(e -> {
                if (app instanceof BackendApp b) b.changeReload(reload.isSelected());
                if (app.process != null) warn("Restart the backend for this to take effect.");
            });
            portField.addActionListener(e -> applyPort());
            portField.addFocusListener(new FocusAdapter() {
                @Override
                public void focusLost(FocusEvent e) {
                    applyPort();
                }
            });
            filter.getDocument().addDocumentListener(new javax.swing.event.DocumentListener() {
                public void insertUpdate(javax.swing.event.DocumentEvent e) { renderLog(); }
                public void removeUpdate(javax.swing.event.DocumentEvent e) { renderLog(); }
                public void changedUpdate(javax.swing.event.DocumentEvent e) { renderLog(); }
            });
            problems.addActionListener(e -> renderLog());
            follow.addActionListener(e -> { if (follow.isSelected()) scrollToEnd(); });

            app.listeners.add(() -> SwingUtilities.invokeLater(this::refresh));
            new Timer(200, e -> drainLog()).start();
            new Timer(1000, e -> refreshFacts()).start();
            refresh();
            renderLog();
        }

        private JComponent buildHeader() {
            JPanel head = new JPanel();
            head.setLayout(new BoxLayout(head, BoxLayout.Y_AXIS));
            head.setBorder(new EmptyBorder(12, 14, 8, 14));

            JLabel name = new JLabel(app.label);
            name.setFont(name.getFont().deriveFont(Font.BOLD, 16f));
            status.setFont(status.getFont().deriveFont(Font.BOLD));
            JPanel titleRow = row(name, Box.createHorizontalStrut(10), status);
            JLabel sub = new JLabel(app.subtitle);
            sub.setForeground(IDLE);
            facts.setForeground(IDLE);
            address.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
            address.setToolTipText("Open in the browser");
            address.addMouseListener(new java.awt.event.MouseAdapter() {
                @Override
                public void mouseClicked(java.awt.event.MouseEvent e) {
                    openBrowser(app.address());
                }
            });

            JPanel buttons = row(start, stop, restart, open);
            JLabel portLabel = new JLabel("Port");
            JPanel options = app instanceof BackendApp
                    ? row(portLabel, Box.createHorizontalStrut(6), portField, Box.createHorizontalStrut(14), keep,
                            Box.createHorizontalStrut(10), reload)
                    : row(portLabel, Box.createHorizontalStrut(6), portField, Box.createHorizontalStrut(14), keep);
            keep.setToolTipText("Restart automatically if the app exits on its own");
            reload.setToolTipText("uvicorn --reload: restart the backend when a .py file changes");
            portField.setToolTipText("Editable while the app is stopped. Press Enter to apply.");
            portField.setMaximumSize(portField.getPreferredSize());

            message.setBorder(new EmptyBorder(6, 0, 0, 0));
            freePort.setToolTipText("Stops the leftover Turbo EA process so this panel can start its own");
            JPanel messageRow = row(message, Box.createHorizontalStrut(8), freePort);

            head.add(titleRow);
            head.add(Box.createVerticalStrut(2));
            head.add(row(sub));
            head.add(Box.createVerticalStrut(2));
            head.add(row(facts, Box.createHorizontalStrut(6), address));
            head.add(Box.createVerticalStrut(10));
            head.add(buttons);
            head.add(Box.createVerticalStrut(8));
            head.add(options);
            head.add(messageRow);
            return head;
        }

        private JComponent buildLog() {
            log.setEditable(false);
            log.setBackground(LOG_BG);
            log.setForeground(LOG_TEXT);
            log.setCaretColor(LOG_TEXT);
            log.setFont(monoFont());
            log.setBorder(new EmptyBorder(6, 10, 6, 10));
            java.awt.event.MouseAdapter links = new java.awt.event.MouseAdapter() {
                @Override
                public void mouseClicked(java.awt.event.MouseEvent e) {
                    String url = linkAt(e.getPoint());
                    if (url != null && log.getSelectedText() == null) openBrowser(url);
                }

                @Override
                public void mouseMoved(java.awt.event.MouseEvent e) {
                    log.setCursor(linkAt(e.getPoint()) != null
                            ? Cursor.getPredefinedCursor(Cursor.HAND_CURSOR)
                            : Cursor.getPredefinedCursor(Cursor.TEXT_CURSOR));
                }
            };
            log.addMouseListener(links);
            log.addMouseMotionListener(links);
            JScrollPane scroll = new JScrollPane(log);
            scroll.setBorder(BorderFactory.createEmptyBorder());
            scroll.getVerticalScrollBar().setUnitIncrement(16);

            JButton copy = new JButton("Copy");
            JButton clear = new JButton("Clear");
            copy.addActionListener(e -> {
                StringBuilder sb = new StringBuilder();
                for (LogLine l : app.logSnapshot()) if (matches(l)) sb.append(l.text()).append('\n');
                Toolkit.getDefaultToolkit().getSystemClipboard().setContents(new StringSelection(sb.toString()), null);
            });
            clear.addActionListener(e -> { app.clearLogs(); renderLog(); });
            filter.setToolTipText("Show only lines containing this text");

            JPanel bar = row(new JLabel("Filter "), filter, Box.createHorizontalStrut(10), problems,
                    Box.createHorizontalStrut(6), follow, Box.createHorizontalGlue(), copy, Box.createHorizontalStrut(4), clear);
            bar.setBorder(BorderFactory.createCompoundBorder(
                    new MatteBorder(1, 0, 0, 0, new Color(0xDFE2E7)), new EmptyBorder(6, 10, 6, 10)));
            filter.setMaximumSize(new Dimension(260, filter.getPreferredSize().height));

            JPanel box = new JPanel(new BorderLayout());
            box.add(bar, BorderLayout.NORTH);
            box.add(scroll, BorderLayout.CENTER);
            return box;
        }

        private static JPanel row(Component... parts) {
            JPanel p = new JPanel();
            p.setLayout(new BoxLayout(p, BoxLayout.X_AXIS));
            p.setAlignmentX(Component.LEFT_ALIGNMENT);
            for (Component c : parts) {
                p.add(c);
                if (c instanceof JButton) p.add(Box.createHorizontalStrut(6));
            }
            p.add(Box.createHorizontalGlue());
            return p;
        }

        private static SimpleAttributeSet style(Color color, boolean italic) {
            SimpleAttributeSet s = new SimpleAttributeSet();
            StyleConstants.setForeground(s, color);
            StyleConstants.setItalic(s, italic);
            return s;
        }

        private void warn(String text) {
            JOptionPane.showMessageDialog(this, text, app.label, JOptionPane.WARNING_MESSAGE);
        }

        private void applyPort() {
            String text = portField.getText().trim();
            if (text.equals(Integer.toString(app.port))) return;
            int next;
            try {
                next = Integer.parseInt(text);
            } catch (NumberFormatException e) {
                portField.setText(Integer.toString(app.port));
                warn("Port must be a whole number between 1024 and 65535.");
                return;
            }
            String problem = app.changePort(next, all);
            if (problem != null) {
                portField.setText(Integer.toString(app.port));
                warn(problem);
                return;
            }
            if (app instanceof BackendApp) {
                for (ManagedApp other : all) {
                    if (other instanceof FrontendApp && other.process != null) {
                        warn("Restart the frontend so it proxies to the new backend port.");
                    }
                }
            }
        }

        private void refresh() {
            State s = app.state;
            status.setText("● " + s.label);
            status.setForeground(toneColor(s.tone));

            boolean idle = s.idle();
            start.setEnabled(idle);
            stop.setEnabled(!idle && s != State.STOPPING);
            restart.setEnabled(s == State.RUNNING || s == State.STARTING);
            open.setEnabled(s == State.RUNNING);
            portField.setEnabled(idle);
            if (!portField.isFocusOwner()) portField.setText(Integer.toString(app.port));
            keep.setSelected(app.keepRunning);
            if (app instanceof BackendApp b) reload.setSelected(b.reload);

            String text = app.message;
            PortOwner o = app.owner;
            if (text.isEmpty() && idle && o != null) text = "Port " + app.port + " is in use by " + o.text() + ".";
            message.setText(text.isEmpty() ? " " : "<html>" + escape(text) + "</html>");
            message.setForeground(s.tone == Tone.BAD ? BAD : s.tone == Tone.BUSY ? BUSY : IDLE);
            freePort.setVisible(idle && o != null && o.ours());
            refreshFacts();
            revalidate();
        }

        private void refreshFacts() {
            Process p = app.process;
            String pid = p != null ? Long.toString(p.pid()) : "-";
            String up = app.state == State.RUNNING && app.startedAt > 0 ? uptime(System.currentTimeMillis() - app.startedAt) : "-";
            facts.setText("Port " + app.port + "   ·   PID " + pid + "   ·   Up " + up + "   ·");
            address.setText("<html><a href=''>" + escape(app.address()) + "</a></html>");
        }

        private static String uptime(long ms) {
            long s = ms / 1000;
            if (s < 60) return s + "s";
            long m = s / 60;
            if (m < 60) return m + "m " + (s % 60) + "s";
            return (m / 60) + "h " + (m % 60) + "m";
        }

        private static String escape(String text) {
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
        }

        private boolean matches(LogLine line) {
            if (problems.isSelected() && line.level() != Level.ERROR && line.level() != Level.WARN) return false;
            String q = filter.getText().trim().toLowerCase(Locale.ROOT);
            return q.isEmpty() || line.text().toLowerCase(Locale.ROOT).contains(q);
        }

        private void renderLog() {
            app.pending.clear();
            app.cleared = false;
            StyledDocument doc = log.getStyledDocument();
            try {
                doc.remove(0, doc.getLength());
            } catch (BadLocationException ignored) {
                // Empty already.
            }
            docLines = 0;
            for (LogLine line : app.logSnapshot()) if (matches(line)) insert(doc, line);
            if (follow.isSelected()) scrollToEnd();
        }

        private void drainLog() {
            if (app.cleared) {
                renderLog();
                return;
            }
            if (app.pending.isEmpty()) return;
            StyledDocument doc = log.getStyledDocument();
            LogLine line;
            while ((line = app.pending.poll()) != null) if (matches(line)) insert(doc, line);
            if (docLines > LOG_LIMIT + 500) {
                renderLog();
                return;
            }
            if (follow.isSelected()) scrollToEnd();
        }

        private void insert(StyledDocument doc, LogLine line) {
            SimpleAttributeSet style;
            switch (line.level()) {
                case ERROR: style = errorStyle; break;
                case WARN: style = warnStyle; break;
                case PANEL: style = panelStyle; break;
                default: style = infoStyle; break;
            }
            try {
                doc.insertString(doc.getLength(), clock.format(new Date(line.time())) + "  ", timeStyle);
                String text = line.text();
                Matcher m = URL.matcher(text);
                int at = 0;
                while (m.find()) {
                    // A sentence's full stop or comma is not part of the address.
                    String url = m.group().replaceAll("[.,;:]+$", "");
                    doc.insertString(doc.getLength(), text.substring(at, m.start()), style);
                    SimpleAttributeSet link = new SimpleAttributeSet(style);
                    StyleConstants.setForeground(link, linkColor);
                    StyleConstants.setUnderline(link, true);
                    link.addAttribute(LINK_ATTR, url);
                    doc.insertString(doc.getLength(), url, link);
                    at = m.start() + url.length();
                }
                doc.insertString(doc.getLength(), text.substring(at) + "\n", style);
                docLines++;
            } catch (BadLocationException ignored) {
                // Appending at the end cannot be out of range.
            }
        }

        /** The URL under a point in the log, or null. */
        private String linkAt(Point p) {
            int pos = log.viewToModel2D(p);
            if (pos < 0) return null;
            Object url = log.getStyledDocument().getCharacterElement(pos).getAttributes().getAttribute(LINK_ATTR);
            return url instanceof String s ? s : null;
        }

        private void scrollToEnd() {
            log.setCaretPosition(log.getDocument().getLength());
        }
    }
}
