# Aline Quintino Acessórios — demonstração de UX e conversão

Frontend estático (HTML, CSS e JavaScript), isolado em `aline-quintino/` para não alterar os demais serviços do repositório.

## Jornada
- Página inicial, categorias e seleções de presentes baseadas no catálogo ilustrativo.
- Rotas compartilháveis `/produto/<slug>` e `/colecao/<categoria>`, com fallback SPA de `vercel.json`.
- Sacola com variante, quantidade, subtotal e persistência em `localStorage`.
- Finalização de **demonstração**: nenhum pedido ou pagamento real.
- Deep links com UTM funcionam sem necessidade de parâmetros adicionais.
- Sem pixels, analytics externos ou avaliações inventadas.

## Operação
A demonstração deve ser implantada com a pasta `aline-quintino` como raiz (ou hospedada como projeto separado). Para desenvolvimento local: `npx serve -s aline-quintino`, ou servidor estático que aceite fallback SPA.

## Pendências
Fotos reais de detalhe e no corpo, catálogo, preço, variações e estoque reais, material, dimensões e cuidados, número oficial para dúvidas, entrega por região/custo/prazo, política de troca, avaliações autorizadas, checkout e políticas.

## Verificações
Sem package.json no diretório da demo: não existem scripts npm de build/lint/test previamente configurados. O HTML/CSS/JS são estáticos. Conferir rotas diretas no deploy, UTM, sacola e teclado.
