# Testes e evidências

O projeto tem dois grupos de testes. Os dois usam o **PostgreSQL real**. Só o segundo usa o **Gemini real**.

| Grupo | O que prova | Quantos | Gasta créditos? | Como rodar |
|---|---|---|---|---|
| **Unitários e de integração** (`tests/`) | Regras de código: exclusividade sob concorrência, confirmação, apartamento da sessão, tools | 19 | Não | `uv run pytest` |
| **E2e, ponta a ponta** (`tests/e2e/`) | O fluxo completo do avaliador (passos 1 a 14) contra a API de verdade, com o Gemini | 14 passos (44 verificações) | **Sim** (cerca de 40 chamadas ao modelo, ~3 minutos) | `uv run pytest -m e2e` |

## Pré-requisitos

- Postgres no ar: `docker compose up -d`
- `.env` preenchido (`GOOGLE_API_KEY`, `MODELO_PRINCIPAL`, `MODELO_ESPECIALISTAS`). Sem ele, os testes e2e são ignorados com uma mensagem.

## Unitários e de integração

```bash
uv run pytest
```

Usam o banco `aurora_test`, criado e restaurado automaticamente. Não chamam o modelo: testam o que o código garante **independentemente** do que o modelo decide.

- [tests/test_repositorio.py](../tests/test_repositorio.py): estado inicial; reserva ocupada recusada sem erro; **24 reservas simultâneas resultam em exatamente 1** (Garantia 5); cancelar só o próprio apartamento; código nunca repete nem após cancelar; visitante idempotente; **10 respostas simultâneas à mesma confirmação, só 1 vence** (Garantia 1).
- [tests/test_tools.py](../tests/test_tools.py): área com taxa exige confirmação e nada é gravado antes; negar não grava; aprovar grava uma vez; quadra não pede confirmação; visitante sempre pede; cancelar reserva alheia não altera nem vaza `RSV-4821`; data ocupada por outro não vaza; **nenhuma tool aceita `apartamento` como parâmetro** (Garantia 2).

## E2e (ponta a ponta)

```bash
uv run pytest -m e2e
```

O que acontece:

1. Cria o banco `aurora_e2e` (separado do de desenvolvimento) e o restaura ao estado inicial.
2. Sobe a API (uvicorn, porta **8001**, para não colidir com a 8000) apontando para esse banco.
3. Executa os passos 1 a 14 do fluxo do avaliador, com as mesmas mensagens do enunciado.
4. No passo 13, **para a API e sobe de novo, sem restaurar**, e confere que a sessão continua e os dados permanecem.
5. No passo 14, dispara as duas aprovações **ao mesmo tempo**, em threads.
6. Grava o relatório em [docs/evidencias/e2e-ultima-execucao.md](evidencias/e2e-ultima-execucao.md).

Ajustes opcionais por variável de ambiente: `E2E_PORTA` (porta da API) e `E2E_RELATORIO` (onde gravar o relatório).

### Mapa: passo do avaliador → teste

| Passo | Teste (`tests/e2e/test_fluxo_avaliador.py`) | Garantia |
|---|---|---|
| 1 | `test_passo_01_dados_iniciais` | dados |
| 2 | `test_passo_02_criar_sessao` | contrato |
| 3 | `test_passo_03_dados_de_outro_apartamento` | 2 |
| 4 | `test_passo_04_cancelar_reserva_de_outro` | 2 |
| 5 | `test_passo_05_cancelar_a_propria_reserva` | 1 (sem confirmação) |
| 6 | `test_passo_06_reservar_area_sem_taxa` | 1 (sem confirmação) |
| 7 | `test_passo_07_negar_confirmacao` | 1 |
| 8 | `test_passo_08_aprovar_e_reenviar` | 1 |
| 9 | `test_passo_09_id_inexistente_e_sessao_inexistente` | 1 |
| 10 | `test_passo_10_data_ocupada_pelo_302` | 2 |
| 11 | `test_passo_11_visitante_com_confirmacao` | 1 |
| 12 | `test_passo_12_regulamento_sem_vazamento` | 4 |
| 13 | `test_passo_13_reinicio` | 3 |
| 14 | `test_passo_14_disputa_simultanea` | 5 |

### Observações importantes

- **Os passos são sequenciais e compartilham estado**, como no fluxo do avaliador. Rode o módulo inteiro, não testes isolados.
- **O modelo não é determinístico.** As garantias de código valem sempre, mas a redação da resposta muda de uma execução para outra. As verificações olham para os **efeitos** (rotas de verificação, eventos) e só olham o texto onde o enunciado manda (por exemplo, o horário de fechamento da piscina). Se um passo falhar por causa do texto do modelo, o relatório mostra qual resposta veio.
- O relatório é regravado a cada execução. A versão commitada mostra a execução de referência.
