"""Prompts do Experimento D: extração dos 5 campos a partir do TEXTO (não imagem) do TRCT.

Mesmos 5 campos e avisos da C, redigidos para "o TEXTO a seguir foi extraído de um formulário
TRCT" — o texto é o do PDF inteiro (todas as páginas).
"""

SYSTEM_PROMPT = (
    "Você extrai dados de TRCT (Termo de Rescisão do Contrato de Trabalho) a partir do TEXTO "
    "do formulário e responde APENAS com um JSON. Nunca invente: campo ausente = string vazia."
)

USER_PROMPT = (
    "O TEXTO a seguir foi extraído de um formulário TRCT padronizado, com campos numerados. Extraia "
    "exatamente estes 5 campos e responda APENAS com um JSON válido (sem markdown, sem comentários):\n"
    "- nome_trabalhador: campo 11 \"Nome\" (o TRABALHADOR; NÃO use o campo 20 \"Nome da mãe\").\n"
    "- nome_empregador: campo 02 \"Razão Social/Nome\" (o EMPREGADOR; NÃO use o campo 11).\n"
    "- ultima_remuneracao: campo 23 \"Remuneração Mês Ant.\" (valor como aparece, ex.: 1.843,25).\n"
    "- data_admissao: campo 24 \"Data de Admissão\" (dd/mm/aaaa).\n"
    "- data_demissao: campo 26 \"Data de Afastamento\" (é a DEMISSÃO; NÃO use o campo 25 \"Aviso prévio\").\n"
    "Datas em dd/mm/aaaa; valor exatamente como no documento; \"\" se ausente; PROIBIDO inventar.\n"
    "Responda só o JSON com exatamente estas chaves: "
    '{"nome_trabalhador":"","nome_empregador":"","ultima_remuneracao":"","data_admissao":"","data_demissao":""}'
)
