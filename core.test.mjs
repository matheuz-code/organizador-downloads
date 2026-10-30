import test from 'node:test';import assert from 'node:assert/strict';import {category,plan} from './core.mjs';
test('categorias e extensões maiúsculas',()=>{assert.equal(category('FOTO.JPG'),'Imagens');assert.equal(category('semextensao'),'Outros');assert.equal(category('x.csv'),'Planilhas');});
test('resolve repetidos e destinos existentes sem sobrescrever',()=>{const p=plan([{name:'a.pdf'},{name:'a.pdf'},{name:'A.PDF'}],['Documentos/a.pdf']);assert.deepEqual(p.map(r=>r.destination),['Documentos/a (1).pdf','Documentos/a (2).pdf','Documentos/A (3).PDF']);});
test('ignora arquivos ocultos, incompletos e caminhos inválidos',()=>{const p=plan([{name:'.oculto'},{name:'x.crdownload'},{name:'../x.pdf'},{name:'organizador-operacoes.jsonl'}]);assert.ok(p.every(r=>r.status==='Ignorado'));});
test('não altera entrada e aceita lista vazia',()=>{const f=[{name:'a.txt',size:2}],copy=JSON.stringify(f);plan(f);assert.equal(JSON.stringify(f),copy);assert.deepEqual(plan([]),[]);});
