/*
 * Setuid helper for SQM (freestanding; no libc).
 * Matches IPFire qosctrl: installed -rwsr-x--- root:nobody.
 * Linux ignores setuid on shell scripts, so this binary raises to uid 0
 * then execs /usr/lib/sqm/sqmctrl.sh.
 *
 * GPL-2.0
 */

#define SYS_write  1
#define SYS_execve 59
#define SYS_exit   60
#define SYS_setuid 105
#define SYS_setgid 106

#define SCRIPT "/usr/lib/sqm/sqmctrl.sh"

static long sys3(long n, long a, long b, long c)
{
	long ret;
	__asm__ volatile ("syscall"
		: "=a"(ret)
		: "a"(n), "D"(a), "S"(b), "d"(c)
		: "rcx", "r11", "memory");
	return ret;
}

static void die(const char *s)
{
	const char *p = s;
	while (*p)
		p++;
	sys3(SYS_write, 2, (long)s, p - s);
	sys3(SYS_exit, 1, 0, 0);
	for (;;)
		;
}

void _start(void)
{
	long *stack;
	long argc;
	char **argv;
	char **envp;

	__asm__ volatile ("mov %%rsp, %0" : "=r"(stack));
	argc = stack[0];
	argv = (char **)(stack + 1);
	envp = argv + argc + 1;

	if (sys3(SYS_setgid, 0, 0, 0) != 0)
		die("sqmctrl: setgid failed\n");
	if (sys3(SYS_setuid, 0, 0, 0) != 0)
		die("sqmctrl: setuid failed\n");

	argv[0] = SCRIPT;
	sys3(SYS_execve, (long)SCRIPT, (long)argv, (long)envp);
	die("sqmctrl: execv /usr/lib/sqm/sqmctrl.sh failed\n");
}
