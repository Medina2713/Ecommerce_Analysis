function getVendas() {
    // Exibe a mensagem enquanto a requisição está sendo processada
    document.getElementById("mensagem").innerHTML = "Aguardando resultado...";
    
    // Faz a requisição GET para o endpoint
    fetch('/get_vendas')
        .then(response => response.json())
        .then(data => {
            // Exibe o resultado na página
            if (data.mensagem) {
                document.getElementById("mensagem").innerHTML = data.mensagem;
            }
            if (data.resultado) {
                document.getElementById("resultado").innerHTML = JSON.stringify(data.resultado, null, 2);
            }
        })
        .catch(error => {
            // Em caso de erro
            document.getElementById("mensagem").innerHTML = "Erro ao chamar a função!";
            console.error('Erro:', error);
        });
}

