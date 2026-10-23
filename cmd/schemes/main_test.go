package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestWrap(t *testing.T) {
	got := wrap("one two three four", 12)
	if len(got) != 2 || got[0] != "one two" || got[1] != "three four" {
		t.Fatalf("wrap = %#v", got)
	}
}

func TestOutline(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "RULES.md")
	body := "# Title\n\n## Section\n\n- bullet one\n- bullet two\n\n```\ncode\n```\n"
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	lines, err := outline(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(lines) < 4 {
		t.Fatalf("lines = %#v", lines)
	}
	if lines[0].kind != "h2" || lines[1].kind != "h2" || lines[2].kind != "bullet" {
		t.Fatalf("kinds = %#v", lines)
	}
	for _, item := range lines {
		if item.text == "code" {
			t.Fatal("code fence content leaked into outline")
		}
	}
}

func TestRender(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "RULES.md"), []byte("# Rules\n\n## One\n\nText.\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	cfg := config{Version: "1.2.3", Date: "01.01.2026"}
	svg, err := render(dir, "docs/scheme-rules.svg", []string{"RULES.md"}, cfg)
	if err != nil {
		t.Fatal(err)
	}
	text := string(svg)
	if !strings.Contains(text, "<svg") || !strings.Contains(text, "Правила") || !strings.Contains(text, "1.2.3") {
		t.Fatalf("unexpected svg: %s", text)
	}
}

func TestTitleFor(t *testing.T) {
	if got := titleFor("docs/scheme-process.svg"); got != "Процесс" {
		t.Fatalf("title = %q", got)
	}
}
