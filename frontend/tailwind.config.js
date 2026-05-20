export default {
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    theme: {
        extend: {
            colors: {
                ink: "var(--color-ink)",
                paper: "var(--color-paper)",
                mist: "var(--color-mist)",
                peach: "var(--color-peach)",
                moss: "var(--color-moss)",
                amber: "var(--color-amber)",
                line: "var(--color-line)",
            },
            boxShadow: {
                soft: "var(--shadow-soft)",
                card: "var(--shadow-card)",
            },
            borderRadius: {
                panel: "var(--radius-panel)",
            },
            fontFamily: {
                sans: ["'Noto Sans SC'", "'PingFang SC'", "system-ui", "sans-serif"],
                serif: ["'Noto Serif SC'", "'Songti SC'", "serif"],
            },
            backgroundImage: {
                "paper-wash": "radial-gradient(circle at top left, rgba(255,244,229,0.9), transparent 38%), radial-gradient(circle at 80% 20%, rgba(216,233,222,0.7), transparent 25%), linear-gradient(180deg, rgba(255,251,245,1), rgba(250,246,239,1))",
            },
        },
    },
    plugins: [],
};
