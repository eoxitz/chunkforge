# ChunkForge online — Minecraft Bedrock

Um website responsivo para Safari no iPhone e outros navegadores. Importa .mcworld ou .zip, escolhe dimensão e região X/Z e entrega uma cópia .mcworld com registros de chunks selecionados removidos.

## Hospedar no Render

1. Crie um repositório GitHub e envie os arquivos deste pacote para a raiz do repositório.
2. Em https://dashboard.render.com/ escolha New > Blueprint e conecte o repositório.
3. Confirme o serviço descrito em render.yaml. O plano `starter` é pago; não há dependência de serviço no seu iPhone.
4. Ao terminar a implantação, abra a URL HTTPS fornecida pelo Render no Safari.

## Limitações e segurança

- **Faça backup.** Operação destrutiva e experimental; incompatibilidades podem ocorrer com mundos novos e dados de entidades.
- Alguns mobs/entidades são guardados separadamente no banco e podem não ser removidos completamente.
- O servidor recebe o arquivo de mundo temporariamente; escolha uma hospedagem confiável. Os dados de upload são excluídos após a requisição.
- Arquivo comprimido até 1 GiB, descompactado até 4 GiB, seleção de até 50.000 chunks; a hospedagem deve ter espaço de disco e memória suficientes.
- O mundo original no aparelho não é alterado.
- Não inclui hospedagem/URL pública automaticamente; é preciso fazer a implantação.
