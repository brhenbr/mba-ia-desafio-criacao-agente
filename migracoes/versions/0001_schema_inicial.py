"""Schema inicial do condominio: apartamentos, areas, reservas, visitantes e confirmacoes.

Revision ID: 0001
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Os codigos gerados pelo sistema comecam em 10000, acima dos codigos do estado
    # inicial (RSV-1377, RSV-4821, RSV-2950). A chave primaria garante que um codigo
    # nunca se repete, e o cancelamento e logico, entao um codigo cancelado continua ocupado.
    op.execute("CREATE SEQUENCE condominio.reserva_codigo_seq START 10000")

    op.execute(
        """
        CREATE TABLE condominio.apartamentos (
            numero  text PRIMARY KEY,
            morador text NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE condominio.areas (
            id   text PRIMARY KEY,
            nome text NOT NULL,
            taxa numeric(10, 2) NOT NULL CHECK (taxa >= 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE condominio.reservas (
            codigo       text PRIMARY KEY
                         DEFAULT 'RSV-' || nextval('condominio.reserva_codigo_seq'),
            apartamento  text NOT NULL REFERENCES condominio.apartamentos (numero),
            area         text NOT NULL REFERENCES condominio.areas (id),
            data         date NOT NULL,
            status       text NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'cancelada')),
            criada_em    timestamptz NOT NULL DEFAULT now(),
            cancelada_em timestamptz
        )
        """
    )
    # GARANTIA 5: no maximo uma reserva ATIVA por area e data. A exclusividade vale
    # no instante da gravacao, e nao numa conferencia feita antes.
    op.execute(
        """
        CREATE UNIQUE INDEX reservas_area_data_ativa_uq
            ON condominio.reservas (area, data) WHERE status = 'ativa'
        """
    )
    op.execute("CREATE INDEX reservas_apartamento_idx ON condominio.reservas (apartamento)")

    op.execute(
        """
        CREATE TABLE condominio.visitantes (
            id          bigserial PRIMARY KEY,
            apartamento text NOT NULL REFERENCES condominio.apartamentos (numero),
            nome        text NOT NULL,
            data        date NOT NULL,
            criada_em   timestamptz NOT NULL DEFAULT now(),
            UNIQUE (apartamento, nome, data)
        )
        """
    )

    # Confirmacoes pendentes (decisao 007). O estado so muda de 'pendente' uma vez.
    op.execute(
        """
        CREATE TABLE condominio.confirmacoes (
            id            text PRIMARY KEY,
            sessao_id     text NOT NULL,
            acao          text NOT NULL,
            detalhes      jsonb NOT NULL DEFAULT '{}'::jsonb,
            estado        text NOT NULL DEFAULT 'pendente'
                          CHECK (estado IN ('pendente', 'aprovada', 'negada')),
            criada_em     timestamptz NOT NULL DEFAULT now(),
            respondida_em timestamptz
        )
        """
    )
    op.execute("CREATE INDEX confirmacoes_sessao_idx ON condominio.confirmacoes (sessao_id)")


def downgrade() -> None:
    op.execute("DROP TABLE condominio.confirmacoes")
    op.execute("DROP TABLE condominio.visitantes")
    op.execute("DROP TABLE condominio.reservas")
    op.execute("DROP TABLE condominio.areas")
    op.execute("DROP TABLE condominio.apartamentos")
    op.execute("DROP SEQUENCE condominio.reserva_codigo_seq")
