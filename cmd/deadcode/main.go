package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type finding struct {
	Pos  string `json:"pos"`
	Kind string `json:"kind"`
	Name string `json:"name"`
}

type decl struct {
	name string
	kind string
	pos  token.Position
	keep bool
}

type pkg struct {
	refs   map[string]int
	decls  []decl
	ifaces map[string]bool
}

var skipDirs = map[string]bool{
	".git": true, "vendor": true, "node_modules": true, "__pycache__": true,
}

func main() {
	jsonOut := flag.Bool("json", false, "write JSON array")
	flag.Parse()
	root := "."
	if flag.NArg() > 0 {
		root = flag.Arg(0)
	}
	findings, err := analyze(root)
	if err != nil {
		fmt.Fprintln(os.Stderr, "deadcode:", err)
		os.Exit(2)
	}
	if *jsonOut {
		if findings == nil {
			findings = []finding{}
		}
		encoder := json.NewEncoder(os.Stdout)
		encoder.SetIndent("", "  ")
		if encodeErr := encoder.Encode(findings); encodeErr != nil {
			fmt.Fprintln(os.Stderr, "deadcode:", encodeErr)
			os.Exit(2)
		}
	} else {
		for _, item := range findings {
			fmt.Printf("%s: %s %s is unused\n", item.Pos, item.Kind, item.Name)
		}
	}
	if len(findings) > 0 {
		os.Exit(1)
	}
}

func analyze(root string) ([]finding, error) {
	fset := token.NewFileSet()
	pkgs := map[string]*pkg{}
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			if skipDirs[entry.Name()] {
				return filepath.SkipDir
			}
			if path != root {
				if _, statErr := os.Stat(filepath.Join(path, "go.mod")); statErr == nil {
					return filepath.SkipDir
				}
			}
			return nil
		}
		if !strings.HasSuffix(path, ".go") {
			return nil
		}
		file, parseErr := parser.ParseFile(fset, path, nil, parser.ParseComments)
		if parseErr != nil {
			return fmt.Errorf("%s: %w", path, parseErr)
		}
		dir := filepath.Dir(path)
		info := pkgs[dir]
		if info == nil {
			info = &pkg{refs: map[string]int{}, ifaces: map[string]bool{}}
			pkgs[dir] = info
		}
		ast.Inspect(file, func(node ast.Node) bool {
			switch item := node.(type) {
			case *ast.Ident:
				info.refs[item.Name]++
			case *ast.InterfaceType:
				for _, field := range item.Methods.List {
					for _, name := range field.Names {
						info.ifaces[name.Name] = true
					}
				}
			}
			return true
		})
		if isGenerated(file) {
			return nil
		}
		collect(info, fset, file)
		return nil
	})
	if err != nil {
		return nil, err
	}
	var findings []finding
	for _, info := range pkgs {
		for _, item := range info.decls {
			if item.keep || info.refs[item.name] > 1 {
				continue
			}
			if item.kind == "method" && info.ifaces[item.name] {
				continue
			}
			findings = append(findings, finding{Pos: item.pos.String(), Kind: item.kind, Name: item.name})
		}
	}
	sort.Slice(findings, func(i, j int) bool { return findings[i].Pos < findings[j].Pos })
	return findings, nil
}

func collect(info *pkg, fset *token.FileSet, file *ast.File) {
	for _, node := range file.Decls {
		switch item := node.(type) {
		case *ast.FuncDecl:
			collectFunc(info, fset, item)
		case *ast.GenDecl:
			collectGen(info, fset, item)
		}
	}
}

func collectFunc(info *pkg, fset *token.FileSet, fn *ast.FuncDecl) {
	name := fn.Name.Name
	if !unexported(name) {
		return
	}
	kind := "func"
	if fn.Recv != nil {
		kind = "method"
	}
	info.decls = append(info.decls, decl{
		name: name,
		kind: kind,
		pos:  fset.Position(fn.Pos()),
		keep: hasKeep(fn.Doc),
	})
}

func collectGen(info *pkg, fset *token.FileSet, gen *ast.GenDecl) {
	keepAll := hasKeep(gen.Doc)
	for _, spec := range gen.Specs {
		switch item := spec.(type) {
		case *ast.TypeSpec:
			if unexported(item.Name.Name) {
				info.decls = append(info.decls, decl{
					name: item.Name.Name,
					kind: "type",
					pos:  fset.Position(item.Pos()),
					keep: keepAll || hasKeep(item.Doc),
				})
			}
		case *ast.ValueSpec:
			kind := "var"
			if gen.Tok == token.CONST {
				kind = "const"
			}
			for _, name := range item.Names {
				if unexported(name.Name) {
					info.decls = append(info.decls, decl{
						name: name.Name,
						kind: kind,
						pos:  fset.Position(name.Pos()),
						keep: keepAll || hasKeep(item.Doc),
					})
				}
			}
		}
	}
}

func unexported(name string) bool {
	return name != "" && name != "_" && name != "init" && name != "main" && !ast.IsExported(name)
}

func hasKeep(doc *ast.CommentGroup) bool {
	return doc != nil && strings.Contains(doc.Text(), "deadcode:keep")
}

func isGenerated(file *ast.File) bool {
	for _, group := range file.Comments {
		for _, comment := range group.List {
			if strings.HasPrefix(comment.Text, "// Code generated ") &&
				strings.HasSuffix(comment.Text, "DO NOT EDIT.") {
				return true
			}
		}
	}
	return false
}
