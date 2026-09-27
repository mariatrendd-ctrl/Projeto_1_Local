🚀 LOCALXPOSE MANAGER v14
O LocalXpose Manager é um sistema de automação e gestão de túneis TCP projetado para alta performance. Ele permite a operação de múltiplos slots de conexão, realizando a busca sequencial de portas e mantendo a estabilidade das conexões ativas através de um sistema de blindagem.

🛠️ Especificações Técnicas
Capacidade: Suporte a até 60 slots (distribuídos em 6 tokens de 10 slots cada).
Lógica de Busca: Varredura sequencial em portas locais.
Sistema de Blindagem: Quando uma conexão é estabelecida, o slot é automaticamente "blindado", tornando-o intocável para evitar quedas por instabilidade do sistema.
Auto-Recovery: Detecção de queda de conexão com remoção automática de blindagem e retorno imediato ao estado de busca.
⌨️ Comandos de Operação
O sistema utiliza atalhos de teclado para controle em tempo real:

Letras Minúsculas (a-z): Libera instantaneamente um slot ativo.
Letras Maiúsculas (A-Z): Adiciona o endpoint à blacklist.
Tecla P: Para a busca em todos os slots que não estão blindados.
Tecla R: Reinicia todo o sistema e remove todas as blindagens.
Tecla ESC: Encerra a aplicação com limpeza de processos.
⚙️ Pré-requisitos
Para o funcionamento correto, é necessário:

Python 3.x instalado.
Dependências:
pip install colorama rich
Copy
LocalXpose: O executável loclx.exe deve estar obrigatoriamente em: C:\loclx-windows-amd64\.
🚀 Como Iniciar
Execute o script via terminal ou IDE.
Na tela de configuração, valide a ativação dos tokens e as portas de saída.
Pressione ENTER para iniciar a operação.
Acompanhe a grade de status:
🟢 Online: Slot buscando conexão.
⚡ Conectado: Conexão estabelecida e blindada.
🔴 Offline: Slot inativo ou sem token.
Desenvolvido por T H E
