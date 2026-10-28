"""Build the Ukrainian help-article targets with their Portuguese translations.

Maps each Ukrainian help string (title or body) to the corresponding English
literal, reusing the catalog translation. Two very long articles are translated
manually here because they were excluded from the catalog by the size filter.
"""
import json

data = open(r"backup\ostriv_original.exe", "rb").read()


def rd(off):
    j = off
    while data[j:j + 2] != b"\x00\x00":
        j += 2
    return data[off:j].decode("utf-16-le")


cat = json.load(open("data/catalog.json", encoding="utf-8"))
pt = {int(k): v for k, v in json.load(open("data/pt_br.json", encoding="utf-8")).items()}
pt_by_en = {e["en"]: pt[e["id"]] for e in cat if e["id"] in pt}
by_en_off = {}
for e in cat:
    for off, enc in e["locs"]:
        if enc == "utf16":
            by_en_off[off] = e["en"]

MAP = {
    0x5A5F80: 0x5AD030,  # Delivery orders body
    0x5A6330: None,      # Supply options body (manual)
    0x5A7CF0: 0x5AD420,  # Special deliveries body
    0x5A82F8: 0x5AD9C8,  # Moving resources title
    0x5A8328: 0x5ADEF8,  # Seasonal hiring title
    0x5A8378: None,      # Supply options title (manual)
    0x5A83A0: 0x5AD9F0,  # Seasonal hiring body
    0x5A8890: 0x5AF870,  # Reporting bugs body
    0x5A9260: 0x5B0260,  # Shelf life body
    0x5A97D0: 0x5B07F8,  # Shelf life title
    0x5A9800: 0x5B0DA0,  # Illnesses body
    0x5A9D48: 0x5B1278,  # Illnesses title
    0x5A9D70: 0x5B0240,  # Reporting bugs title
    0x5A9DB0: 0x5B0D80,  # Stats: treasury title
    0x5A9DE0: 0x5B1500,  # Stats: resources body
    0x5AA6D0: 0x5B0810,  # Stats: treasury body
    0x5AAC90: 0x5B14D8,  # Stats: population title
    0x5AACC0: None,      # Employment body (manual)
    0x5ABDA0: 0x5B1CE0,  # Stats: resources title
    0x5ABDD0: 0x5B12B0,  # Stats: population body
    0x5ACFF8: None,      # Employment title (manual)
    0x5AC050: None,      # Trade limits body (from catalog id 2404)
    0x5ACC00: None,      # Loans body (from catalog id 2407)
}

MANUAL_FROM_ID = {
    0x5AC050: 2404,
    0x5ACC00: 2407,
}

MANUAL = {
    0x5A82F8: "Movimentação de recursos",
    0x5A8378: "Opções de suprimento",
    0x5A9D70: "Como relatar bugs",
    0x5A6330: "Todas as construções que podem receber recursos têm um botão [img ui_button_80.png ui_button_80_resourse_supply.png]\"Suprimento de recursos\" em suas propriedades, que abre a janela de opções de suprimento. Dependendo da construção, esta janela pode conter os seguintes itens:\n[b]Capacidade[/b] - cada construção tem uma certa quantidade de espaço livre para armazenar recursos. Se esse espaço estiver totalmente ocupado, o suprimento para esta construção se torna impossível. Isso é especialmente importante em construções com animais, onde é necessário espaço para armazenar ração.\n[checkbox] [b]Trabalhador a pé[/b] - se marcado, os trabalhadores desta construção fornecerão os recursos necessários sem usar carroças. A quantidade fornecida por viagem é menor do que com uma carroça, mas pode ser mais adequada se o recurso necessário estiver armazenado por perto.\n[checkbox] [b]Trabalhador por carroça[/b] - se marcado, os trabalhadores desta construção fornecerão os recursos necessários com carroças disponíveis nos estacionamentos de carroças próximos. Se a quantidade necessária do recurso for pequena o suficiente, os trabalhadores a entregarão a pé (se esta opção estiver marcada). Dá-se preferência às carroças mais próximas, mas se elas não forem encontradas por muito tempo, carroças mais distantes serão consideradas. Observe que as carroças dos abrigos de carroças só estão disponíveis para seus trabalhadores.\n[checkbox] [b]Braçal a pé[/b] - se marcado, um trabalhador temporário (braçal) será contratado do grupo de desempregados para uma entrega única a pé.\n[checkbox] [b]Braçal por carroça[/b] - o mesmo que o anterior, mas usando uma carroça.\n[checkbox] [b]Carroceiro[/b] - se marcado, a entrega será feita pelo trabalhador do abrigo de carroças onde a opção \"Entrega regular\" foi ativada. Os carroceiros só fornecerão se a quantidade de recurso não for menor que o mínimo para este abrigo de carroças.\n[checkbox] [b]Por carroção[/b] - se marcado, a entrega será realizada pelos trabalhadores do abrigo de carroções se a opção \"Entrega regular\" do abrigo estiver ativada. Os trabalhadores do abrigo de carroções só fornecerão se a quantidade de recurso não for menor que o mínimo para o abrigo deles.\nO suprimento de água é feito apenas a pé. Se ambas as opções \"a pé\" estiverem desativadas, o suprimento de água ainda será feito por trabalhadores e braçais.\n[b]Lista de recursos[/b] - para cada um dos recursos que podem ser fornecidos à construção, você pode definir uma quantidade-alvo. O recurso será fornecido até que essa quantidade seja atingida. Aqui você também pode definir o volume máximo de suprimento anual. Se for atingido, o suprimento parará. Um valor \"0\" significa que o suprimento anual é ilimitado.\nAlgumas construções podem ser tanto receptoras quanto fornecedoras do mesmo recurso. Você pode definir 0 para os recursos que podem ser entregues a outras construções, ou uma quantidade diferente de zero se a construção deve ser receptora. Se uma construção produzir um recurso cujo suprimento está definido como diferente de zero, esse recurso não estará disponível para outras construções e será marcado com um ícone de cadeado na lista.\nPara construções com animais, esta lista pode ser usada para especificar quais tipos de ração serão fornecidos aos animais.\nVocê também pode escolher de quais construções específicas suprir, adicionando-as à lista [b]Fontes de suprimento[/b]. Se a lista estiver vazia, os recursos serão fornecidos do armazenamento mais próximo disponível. O suprimento de água não é afetado por esta lista.",
    0x5AACC0: "Há dois tipos de emprego: [b]trabalhadores[/b] e [b]braçais[/b]. Os trabalhadores são contratados abrindo vagas por um longo período para uma construção específica e recebem salário constante. Os braçais, por outro lado, são contratados automaticamente apenas para tarefas pontuais. Você precisa ter um certo nível de desemprego para preencher rapidamente as vagas de braçais.\nOs cidadãos em Ostriv não podem ser designados manualmente para empregos específicos. Você só pode criar vagas abertas para que eles se candidatem. Os locais onde escolhem trabalhar dependem de vários fatores, como salário, distância de casa e preferência pessoal. Além disso, os empregos de braçal são considerados menos desejáveis.\nPara criar uma vaga, clique no botão [img ui_add_btn.png] nas propriedades da construção. Enquanto procura um trabalhador, você verá o ícone [img ui_wait_btn.png]. As vagas de braçal são criadas automaticamente quando há tarefas de braçal disponíveis.\nVocê pode definir salários nas opções de contratação de cada construção. 100% significa o salário usual (o definido na janela de estatísticas do tesouro). Você pode alterar essa porcentagem para motivar adicionalmente as pessoas a aceitar empregos nesta construção.\nAlguns cargos só podem ser ocupados por homens, mas na maioria dos casos você pode escolher contratar homens, mulheres ou ambos nas opções de contratação. Homens e mulheres podem usar carroças, mas as mulheres carregam 40% menos recursos.\nVocê também pode contratar crianças com mais de 15 anos para trabalhar como braçais. As crianças podem carregar metade do que os braçais adultos e recebem metade do salário. Os braçais infantis tendem a trabalhar mais perto de casa do que os adultos. As crianças não podem usar carroças para entregas.\nCom base na preferência pessoal, alguns cidadãos podem não estar procurando emprego se tiverem dinheiro suficiente para sustentar seu modo de vida por anos. Isso é mais provável em cidades com populações maiores, devido à menor pressão dos pares.\nAlguns cargos, como gerentes ou conselheiros, exigem educação e só podem ser ocupados por cidadãos com nível suficiente de instrução.\nComo o tempo no jogo é acelerado, o dia de trabalho mínimo dura cerca de 4 dias do jogo. Pode ser mais longo se um trabalhador gastar mais tempo se deslocando até o local de trabalho, compensando assim a distância percorrida.",
    0x5ACFF8: "Emprego",
}

targets = []
missing = []
for uk, en in MAP.items():
    if uk in MANUAL:
        pt_text = MANUAL[uk]
    elif uk in MANUAL_FROM_ID:
        pt_text = pt.get(MANUAL_FROM_ID[uk])
    else:
        en_text = by_en_off.get(en)
        pt_text = pt_by_en.get(en_text) if en_text else None
        if not pt_text:
            missing.append((hex(uk), hex(en) if en else None, en_text[:50] if en_text else None))
            continue
    targets.append(dict(uk=uk, en=en, pt=pt_text, uk_text=rd(uk)[:50]))

print("targets:", len(targets), "missing:", missing)
json.dump(targets, open("data/help_targets.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for t in targets:
    print(f"{t['uk']:#x} -> {t['pt'][:60]!r}")
