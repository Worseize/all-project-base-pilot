package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"html"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type config struct {
	Version string              `json:"version"`
	Date    string              `json:"date"`
	Schemes map[string][]string `json:"schemes"`
}

type line struct {
	text string
	kind string
}

var (
	linkRe  = regexp.MustCompile(`\[([^\]]+)\]\([^)]+\)`)
	spaceRe = regexp.MustCompile(`\s+`)
)

func main() {
	write := flag.Bool("write", false, "write SVG files")
	check := flag.Bool("check", false, "check SVG files are current")
	root := flag.String("root", ".", "project root")
	flag.Parse()
	if *write == *check {
		fmt.Fprintln(os.Stderr, "use exactly one of -write or -check")
		os.Exit(2)
	}
	cfg, err := loadConfig(filepath.Join(*root, "project.json"))
	if err != nil {
		fmt.Fprintln(os.Stderr, "schemes:", err)
		os.Exit(2)
	}
	paths := make([]string, 0, len(cfg.Schemes))
	for path := range cfg.Schemes {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	failed := false
	for _, path := range paths {
		svg, err := render(*root, path, cfg.Schemes[path], cfg)
		if err != nil {
			fmt.Fprintln(os.Stderr, "schemes:", err)
			os.Exit(2)
		}
		if *write {
			if err := writeFile(filepath.Join(*root, path), svg); err != nil {
				fmt.Fprintln(os.Stderr, "schemes:", err)
				os.Exit(2)
			}
			fmt.Println("  wrote:", path)
			continue
		}
		current, err := os.ReadFile(filepath.Join(*root, path))
		if err != nil || string(current) != string(svg) {
			fmt.Println("RED:", path, "outdated or missing")
			failed = true
		}
	}
	if failed {
		os.Exit(1)
	}
	if *check {
		fmt.Println("GREEN: SVG schemes are current")
	}
}

func loadConfig(path string) (config, error) {
	var cfg config
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg, err
	}
	if err := json.Unmarshal(data, &cfg); err != nil {
		return cfg, err
	}
	if len(cfg.Schemes) == 0 {
		return cfg, fmt.Errorf("project.json has no schemes")
	}
	return cfg, nil
}

func render(root, output string, sources []string, cfg config) ([]byte, error) {
	var lines []line
	for _, source := range sources {
		text, err := outline(filepath.Join(root, source))
		if err != nil {
			return nil, err
		}
		lines = append(lines, text...)
	}
	height := 150 + len(lines)*24 + 60
	var b strings.Builder
	b.WriteString(`<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="`)
	b.WriteString(fmt.Sprint(height))
	b.WriteString(`" viewBox="0 0 1400 `)
	b.WriteString(fmt.Sprint(height))
	b.WriteString(`">` + "\n")
	b.WriteString(`<rect width="1400" height="100%" fill="#f7f9fc"/>` + "\n")
	b.WriteString(`<style>text{font-family:'DejaVu Sans',Arial,sans-serif;fill:#172033}`)
	b.WriteString(`.title{font-size:32px;font-weight:700}.sub{font-size:14px;fill:#667085}`)
	b.WriteString(`.h2{font-size:22px;font-weight:700;fill:#1d4ed8}`)
	b.WriteString(`.h3{font-size:18px;font-weight:700;fill:#172033}`)
	b.WriteString(`.p{font-size:15px}.bullet{font-size:15px}.table{font-family:'DejaVu Sans Mono',monospace;font-size:13px}`)
	b.WriteString(`</style>` + "\n")
	b.WriteString(`<text x="60" y="64" class="title">` + html.EscapeString(titleFor(output)) + `</text>` + "\n")
	b.WriteString(`<text x="60" y="92" class="sub">Source: ` + html.EscapeString(strings.Join(sources, ", ")) + ` · v` + html.EscapeString(cfg.Version) + ` · ` + html.EscapeString(cfg.Date) + `</text>` + "\n")
	y := 132
	for _, item := range lines {
		class := "p"
		prefix := ""
		switch item.kind {
		case "h2":
			class = "h2"
			y += 12
		case "h3":
			class = "h3"
		case "bullet":
			class = "bullet"
			prefix = "• "
		case "table":
			class = "table"
		}
		b.WriteString(fmt.Sprintf(`<text x="60" y="%d" class="%s">%s</text>`+"\n", y, class, html.EscapeString(prefix+item.text)))
		y += 24
	}
	b.WriteString("</svg>\n")
	return []byte(b.String()), nil
}

func outline(path string) ([]line, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []line
	inCode := false
	for _, raw := range strings.Split(string(data), "\n") {
		text := strings.TrimSpace(raw)
		if strings.HasPrefix(text, "```") {
			inCode = !inCode
			continue
		}
		if inCode || text == "" || text == "---" {
			continue
		}
		kind := "p"
		switch {
		case strings.HasPrefix(text, "### "):
			kind = "h3"
			text = strings.TrimPrefix(text, "### ")
		case strings.HasPrefix(text, "## "):
			kind = "h2"
			text = strings.TrimPrefix(text, "## ")
		case strings.HasPrefix(text, "# "):
			kind = "h2"
			text = strings.TrimPrefix(text, "# ")
		case strings.HasPrefix(text, "- "):
			kind = "bullet"
			text = strings.TrimPrefix(text, "- ")
		case strings.HasPrefix(text, "* "):
			kind = "bullet"
			text = strings.TrimPrefix(text, "* ")
		case strings.HasPrefix(text, "|"):
			if strings.Contains(text, "---") {
				continue
			}
			kind = "table"
			text = strings.Trim(strings.ReplaceAll(text, "|", " "), " ")
		}
		text = clean(text)
		wrapped := wrap(text, 112)
		for i, part := range wrapped {
			lineKind := kind
			if i > 0 {
				lineKind = "p"
			}
			out = append(out, line{text: part, kind: lineKind})
		}
	}
	return out, nil
}

func clean(text string) string {
	text = linkRe.ReplaceAllString(text, "$1")
	text = strings.ReplaceAll(text, "**", "")
	text = strings.ReplaceAll(text, "`", "")
	text = strings.ReplaceAll(text, "[ ]", "")
	text = strings.ReplaceAll(text, "[x]", "")
	return strings.TrimSpace(spaceRe.ReplaceAllString(text, " "))
}

func wrap(text string, width int) []string {
	words := strings.Fields(text)
	if len(words) == 0 {
		return nil
	}
	var lines []string
	current := ""
	for _, word := range words {
		if current == "" {
			current = word
		} else if len(current)+1+len(word) <= width {
			current += " " + word
		} else {
			lines = append(lines, current)
			current = word
		}
	}
	return append(lines, current)
}

func titleFor(path string) string {
	base := filepath.Base(path)
	switch base {
	case "scheme-rules.svg":
		return "Правила"
	case "scheme-strategy.svg":
		return "Стратегия"
	case "scheme-roadmap.svg":
		return "Дорожная карта"
	case "scheme-process.svg":
		return "Процесс"
	case "scheme-isolation.svg":
		return "Изоляция"
	default:
		return strings.TrimSuffix(base, filepath.Ext(base))
	}
}

func writeFile(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}
