// The debugger side of the "universal" JIT protocol.
//
// Runs in QuickJS inside ModStaller (see jit.py). This is our own
// implementation, but it keeps the global names of StikDebug's universal
// script on purpose: apps send extensions (brk #0x68, or brk #0xf00d with
// x16 = 2) that are evaluated right here and expect to find `commands`,
// `legacyCommands`, `x0`, `x1`, `x16`, `pc`, `tid`, `log`, `send_command`,
// `prepare_memory_region`, `JIT26PrepareRegion`, `JIT26Detach` and so on.
// Amethyst's extension, for instance, sets `x1 = x0; x0 = 0;` and then
// calls `JIT26PrepareRegion`.
//
// The host provides __host_send, __host_prepare, __host_log, __host_event,
// __host_pid and __host_txm. They never throw - a failure comes back as a
// string starting with NUL, and the wrappers below turn it into an
// exception.

const LOG_NONE = 0;
const LOG_INFO = 1;
const LOG_VERBOSE = 2;
let logLevel = LOG_VERBOSE;

// The registers of the current stop. Extensions read and write them.
let tid = null, x0 = 0n, x1 = 0n, x16 = 0n, pc = 0n;
let detached = false;
let continuesWithSignal = true;

// -- Host functions ----------------------------------------------------------

function __check(reply) {
    if (typeof reply === "string" && reply.charCodeAt(0) === 0) {
        throw new Error(reply.slice(1));
    }
    return reply;
}

function send_command(command) {
    return __check(__host_send(String(command)));
}

function prepare_memory_region(address, size) {
    return __check(__host_prepare(String(BigInt(address)),
                                  String(BigInt(size))));
}

function log(...parts) {
    __host_log(parts.map(p => String(p)).join(" "));
}

function log_verbose(message) {
    if (logLevel >= LOG_VERBOSE) {
        log(message);
    }
}

function get_pid() {
    return __host_pid();
}

function hasTXM() {
    return __host_txm();
}

// -- Helpers (extensions use these too) ---------------------------------------

function littleEndianHexStringToNumber(hex) {
    let value = 0n;
    for (let i = hex.length - 2; i >= 0; i -= 2) {
        value = (value << 8n) | BigInt(parseInt(hex.substr(i, 2), 16));
    }
    return value;
}

function numberToLittleEndianHexString(value) {
    value = BigInt(value);
    let out = "";
    for (let i = 0; i < 8; i++) {
        out += Number(value & 0xFFn).toString(16).padStart(2, "0");
        value >>= 8n;
    }
    return out;
}

function littleEndianHexToU32(hex) {
    return Number(littleEndianHexStringToNumber(hex.substr(0, 8)));
}

function extractBrkImmediate(instruction) {
    return (instruction >>> 5) & 0xFFFF;
}

function isBrk(instruction) {
    return ((instruction & 0xFFE0001F) >>> 0) === 0xD4200000;
}

function hexToAscii(hex) {
    let text = "";
    for (let i = 0; i < hex.length; i += 2) {
        const byte = parseInt(hex.substr(i, 2), 16);
        if (byte === 0) {
            break;
        }
        text += String.fromCharCode(byte);
    }
    return text;
}

function registersOf(reply) {
    const regs = {};
    const pattern = /([0-9a-f]{2}):([0-9a-f]+);/g;
    let match;
    while ((match = pattern.exec(reply)) !== null) {
        regs[parseInt(match[1], 16)] = match[2];
    }
    return regs;
}

function register(regs, number) {
    const hex = regs[number];
    return hex === undefined ? null : littleEndianHexStringToNumber(hex);
}

function setRegister(number, value) {
    return send_command(
        `P${number.toString(16)}=${numberToLittleEndianHexString(value)};` +
        `thread:${tid};`);
}

// -- Commands --------------------------------------------------------------

function JIT26Detach(brkResponse) {
    send_command("D");
    detached = true;
}

function JIT26PrepareRegion(brkResponse) {
    if (x0 == 0 && x1 == 0) {
        return;
    }
    let address = BigInt(x0);
    if (address === 0n) {
        // The app leaves the choice of address to the debugger.
        const reply = send_command(`_M${BigInt(x1).toString(16)},rx`);
        if (!reply || reply[0] === "E") {
            log(`Could not allocate RX memory (reply: ${reply})`);
            return;
        }
        address = BigInt(`0x${reply}`);
        log_verbose(`Allocated 0x${address.toString(16)}`);
    }
    prepare_memory_region(address, x1);
    setRegister(0, address);
}

function runScriptAndCapture(scriptText) {
    try {
        // A direct eval, so the script sees and changes our globals.
        const value = eval(scriptText);
        return { ok: true, value };
    } catch (err) {
        return { ok: false, name: err && err.name,
                 message: err && err.message };
    }
}

function JIT26NewBreakpoints(brkResponse) {
    const length = Number(BigInt(x1));
    if (!x0 || !length) {
        return;
    }
    const text = hexToAscii(
        send_command(`m${BigInt(x0).toString(16)},${length.toString(16)}`));
    log_verbose(`Script from the app: ${text}`);
    const result = runScriptAndCapture(text);
    if (result.ok) {
        __host_event("script", "");
    } else {
        __host_event("script_failed", `${result.name}: ${result.message}`);
    }
}

// What an app gets back for brk #0x69 without a handler. StikDebug sends
// "P0=E0000069" - and since P takes little-endian bytes, x0 really holds
// 0x690000E0. Apps test for exactly that value to tell the universal script
// from the legacy one (Amethyst: `(uint32_t)result != 0x690000E0` means
// "legacy script, not supported"), so we must match it bit for bit.
const UNIVERSAL_MARKER = 0x690000E0n;

function JIT26HandleBrk0x69(brkResponse) {
    // The old call. Apps use it as a probe, or bring their own handler in an
    // extension (legacyCommands[0x69] = ...).
    log("brk #0x69 without a handler - answering with the universal marker");
    setRegister(0, UNIVERSAL_MARKER);
}

function JIT26HandleBrk0xf00d(brkResponse) {
    const command = commands[x16];
    if (command === undefined) {
        log(`Unknown command 0x${x16.toString(16)}`);
        __host_event("unknown_command", x16.toString());
        return;
    }
    command(brkResponse);
}

const commands = {
    0: JIT26Detach,
    1: JIT26PrepareRegion,
    2: JIT26NewBreakpoints,
};

const legacyCommands = {
    0x68: JIT26NewBreakpoints,
    0x69: JIT26HandleBrk0x69,
    0xf00d: JIT26HandleBrk0xf00d,
};

// -- The conversation --------------------------------------------------------

// Returns why it ended: "detached", "silent", "exited" or "limit".
function main(maxStops) {
    let pending = null;
    let stops = 0;
    while (!detached) {
        if (stops >= maxStops) {
            return "limit";
        }
        stops++;

        const reply = pending !== null ? pending : send_command("c");
        pending = null;
        if (!reply) {
            return "silent";
        }
        if (reply[0] === "W" || reply[0] === "X") {
            return "exited";
        }

        const regs = registersOf(reply);
        const thread = /thread:([0-9a-f]+);/.exec(reply);
        tid = thread ? thread[1] : null;
        pc = register(regs, 0x20);
        x16 = register(regs, 0x10) ?? 0n;
        if (tid === null || pc === null) {
            log(`Stop without thread or pc: ${reply}`);
            continue;
        }

        const instruction = littleEndianHexToU32(
            send_command(`m${pc.toString(16)},4`));
        if (!isBrk(instruction)) {
            // An ordinary signal - pass it on, otherwise the debugger
            // swallows a crash of the app. Its reply is the next stop.
            const signal = /^T([0-9a-f]{2})/.exec(reply);
            if (continuesWithSignal && signal) {
                log_verbose(`Passing on signal 0x${signal[1]}`);
                pending = send_command(`vCont;S${signal[1]}:${tid}`);
            }
            continue;
        }

        const immediate = extractBrkImmediate(instruction);
        log_verbose(`Breakpoint 0x${immediate.toString(16)} at ` +
                    `0x${pc.toString(16)}, x16=0x${x16.toString(16)}`);
        const handler = legacyCommands[immediate];
        if (handler === undefined) {
            log(`Skipped unknown breakpoint 0x${immediate.toString(16)}`);
            continue;
        }

        x0 = register(regs, 0x00) ?? 0n;
        x1 = register(regs, 0x01) ?? 0n;
        // Step over the breakpoint, otherwise the app stops there again.
        setRegister(0x20, pc + 4n);
        handler(reply);
    }
    return "detached";
}
