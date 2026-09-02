# Alergênicos extraídos dos ícones, com estado indeterminado explícito

O cardápio oficial marca alergênicos como ícones (imagens de 52×52) posicionados ao lado de cada prato, sem nenhuma contrapartida textual. Decidimos extraí-los e exibi-los por prato, identificando cada ícone pelo seu object ID no PDF e associando-o ao prato mais próximo por coordenadas. Como essa associação é heurística e o custo de errar é risco à saúde, todo prato carrega um estado explícito — **alergênicos identificados** ou **indeterminado** — e a interface nunca apresenta a ausência de ícones como "não contém".

## Consequences

- O parser precisa de coordenadas de imagem (ex.: PyMuPDF), não só de extração de texto.
- Uma mudança de layout no PDF da UnB não produz alergênicos errados: produz pratos **indeterminados**, que é a falha que queremos.
- A interface tem três estados por prato a suportar, não dois: com alergênicos, sem nenhum alergênico identificado com confiança, e — só quando a extração foi bem-sucedida e nada foi encontrado — genuinamente sem alergênicos marcados.
- O link para o PDF oficial da semana é obrigatório na interface: ele é a saída de quem tem restrição alimentar e encontrou um prato indeterminado.
