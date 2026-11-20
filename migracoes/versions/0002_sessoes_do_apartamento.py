"""Vinculo da sessao ao apartamento (Garantia 2).

Revision ID: 0002
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # O apartamento e gravado UMA vez, na criacao da sessao, e nunca atualizado.
    # O trigger impede qualquer alteracao posterior, mesmo por engano no codigo.
    op.execute(
        """
        CREATE TABLE condominio.sessoes (
            id          text PRIMARY KEY,
            apartamento text NOT NULL REFERENCES condominio.apartamentos (numero),
            criada_em   timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE FUNCTION condominio.sessao_imutavel() RETURNS trigger AS $$
        BEGIN
            IF NEW.apartamento IS DISTINCT FROM OLD.apartamento OR NEW.id IS DISTINCT FROM OLD.id THEN
                RAISE EXCEPTION 'o apartamento de uma sessao nao pode ser alterado';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER sessoes_imutavel BEFORE UPDATE ON condominio.sessoes
            FOR EACH ROW EXECUTE FUNCTION condominio.sessao_imutavel()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER sessoes_imutavel ON condominio.sessoes")
    op.execute("DROP FUNCTION condominio.sessao_imutavel()")
    op.execute("DROP TABLE condominio.sessoes")
