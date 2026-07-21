"""NORA Content Meta Model — Applications Architecture building blocks.

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 1E).

The National EA Framework "EA Content Meta Model" document (§5.3.5) defines the
Applications domain building blocks. ``Application`` and Technical Integration
Interface (= ``Interface``) already exist in ``seed.TYPES``; this module adds the
two decomposition blocks:

    ApplicationModule (§5.3.5.2.2), ApplicationFunction (§5.3.5.2.3)

Both are described by Name + Description only in the document, so they carry no
custom attribute sections. Appended onto ``seed.TYPES``.
"""

from __future__ import annotations

from app.services.seed_nora_technology import _tx

NORA_APPLICATION_TYPES: list[dict] = [
    # 29 · Application Module ----------------------------------------------
    {
        "key": "ApplicationModule",
        "label": "Application Module",
        "description": "A distinct, separate software module within an application that performs "
        "a unique function or a set of related functions.",
        "icon": "widgets",
        "color": "#0f7eb5",
        "category": "Application",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Anwendungsmodul",
                fr="Module d'application",
                es="Módulo de aplicación",
                it="Modulo dell'applicazione",
                pt="Módulo de aplicação",
                zh="应用模块",
                ru="Модуль приложения",
                da="Applikationsmodul",
                ar="وحدة التطبيق",
            ),
            "description": _tx(
                de="Ein eigenständiges Softwaremodul innerhalb einer Anwendung, das eine "
                "eindeutige Funktion oder eine Reihe verwandter Funktionen ausführt.",
                fr="Un module logiciel distinct au sein d'une application, qui exécute une "
                "fonction unique ou un ensemble de fonctions connexes.",
                es="Un módulo de software distinto dentro de una aplicación que realiza una "
                "función única o un conjunto de funciones relacionadas.",
                it="Un modulo software distinto all'interno di un'applicazione che svolge una "
                "funzione unica o un insieme di funzioni correlate.",
                pt="Um módulo de software distinto dentro de uma aplicação que executa uma "
                "função única ou um conjunto de funções relacionadas.",
                zh="应用程序中执行独特功能或一组相关功能的独立软件模块。",
                ru="Отдельный программный модуль в составе приложения, выполняющий уникальную "
                "функцию или набор связанных функций.",
                da="Et distinkt softwaremodul i en applikation, der udfører en unik funktion "
                "eller et sæt relaterede funktioner.",
                ar="وحدة برمجية مستقلة ضمن التطبيق تؤدي وظيفة فريدة أو مجموعة وظائف مترابطة.",
            ),
        },
        "subtypes": [],
        "sort_order": 30,
        "fields_schema": [],
    },
    # 30 · Application Function --------------------------------------------
    {
        "key": "ApplicationFunction",
        "label": "Application Function",
        "description": "A set of software processes that perform a specific task, usually "
        "executed as a function within the application.",
        "icon": "function",
        "color": "#0f7eb5",
        "category": "Application",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Anwendungsfunktion",
                fr="Fonction d'application",
                es="Función de aplicación",
                it="Funzione dell'applicazione",
                pt="Função de aplicação",
                zh="应用功能",
                ru="Функция приложения",
                da="Applikationsfunktion",
                ar="وظيفة التطبيق",
            ),
            "description": _tx(
                de="Eine Reihe von Softwareprozessen, die eine bestimmte Aufgabe ausführen, "
                "üblicherweise als Funktion innerhalb der Anwendung umgesetzt.",
                fr="Un ensemble de processus logiciels qui exécutent une tâche spécifique, "
                "généralement mis en œuvre comme une fonction au sein de l'application.",
                es="Un conjunto de procesos de software que realizan una tarea específica, "
                "normalmente implementados como una función dentro de la aplicación.",
                it="Un insieme di processi software che svolgono un compito specifico, "
                "solitamente eseguiti come funzione all'interno dell'applicazione.",
                pt="Um conjunto de processos de software que executam uma tarefa específica, "
                "normalmente implementados como uma função dentro da aplicação.",
                zh="执行特定任务的一组软件处理，通常作为应用程序中的一个功能来实现。",
                ru="Набор программных процессов, выполняющих определённую задачу, обычно "
                "реализуемый как функция в составе приложения.",
                da="Et sæt af softwareprocesser, der udfører en bestemt opgave, som regel "
                "implementeret som en funktion i applikationen.",
                ar="مجموعة من العمليات البرمجية التي تؤدي مهمة محددة، وتُنفَّذ عادةً كدالة ضمن "
                "التطبيق.",
            ),
        },
        "subtypes": [],
        "sort_order": 31,
        "fields_schema": [],
    },
]
