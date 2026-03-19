# ExpViewer

Visualizador de experimentos.

## Objetivo

Facilitar a visualização e intercomparação de experimentos em relação a:

* Campos meteorológicos (análises e previsões)
* Viés e Raiz do Erro Quadrático Médio

## Uso

A utilização deste visualizador requer que o usuário tenha uma conta ativa na máquina Egeon, onde os scripts serão executados dentro do ambiente conda apropriado, fazendo-se direcionamento de porta do display para visualização em máquina local.

### Na Egeon

Escolha um local adequado na máquina (eg., `/mnt/beegfs/$USER`), faça o clone desse repositório e crie o ambiente conda:

``` 
cd /mnt/beegfs/$USER
module load anaconda3-2022.05-gcc-11.2.0-q74p53i
gh repo clone GAD-DIMNT-CPTEC/ExpViewer
cd ExpViewer
conda env create -f environment.yml
conda activate ExpViewer
``` 

Ainda dentro do diretório `ExpViewer`, execute:

``` 
jupyter-lab --no-browser
``` 

Anote a porta que aparecer logo após o endereço `localhost`, por exemplo `8888` :

``` 
    To access the server, open this file in a browser:
        file:///home/carlos.bastarz/.local/share/jupyter/runtime/jpserver-116719-open.html
    Or copy and paste one of these URLs:
        http://localhost:8888/lab?token=93e753ffae605164a1f1e38c470be9ba30272b8c539fd1ee
        http://127.0.0.1:8888/lab?token=93e753ffae605164a1f1e38c470be9ba30272b8c539fd1ee
``` 

Dessa forma, será aberta uma instância do Jupyter sem a parte gráfica, a qual será acessada na máquina local do usuário.

### Na máquina local

Com o Jupyter em execução na Egeon, abra um novo terminal e execute:

``` 
ssh -N -f -L localhost:8887:localhost:8888 usario@egeon.cptec.inpe.br
``` 

Observe que a porta `8888` do Jupyter em execução na Egeon, será redirecionada para a porta `8887` da máquina local.

Para acessar o notebook `plot_scores.ipynb` que contém o viez e a raiz do erro quadrático médio dos experimentos do SMNA, abra um navegador de internet e acesse o endereço `http://localhost:8887/lab/tree/plot_scores.ipynb` 

Além do script `plot_scores.ipynb` há também o script `plot_fields.py` que permite a intercomparação espacial dos campos dos experimentos. Para acessá-lo, o procedimento é semelhante:

Em um novo terminal na Egeon, mas ainda no diretório `ExpViewer`, execute:

``` 
panel serve plot_fields.py --port 5006 --autoreload
``` 

Em seguida, em um novo terminal na máquina local, digite:

``` 
ssh -N -f -L localhost:5006:localhost:5006 usario@egeon.cptec.inpe.br
``` 

Depois disso, abra uma nova aba no navegador e acesso o endereço `http://localhost:5006/plot_fields`

<img width="1603" height="1570" alt="Screenshot_20260319_170448" src="https://github.com/user-attachments/assets/3f40011c-92f5-489c-86c0-f170ffd3cbc0" />

**Notas:**

* Os dados apresentados são lidos diretamente da Egeon
* Os dados lidos estão no formato Zarr (veja os scripts do repositório https://github.com/GAD-DIMNT-CPTEC/BAM-grib-to-netcdf-to-zarr para ver como os dados foram convertidos de Grib para NetCDF e depois para Zarr)
* Os ddos lidos encontram-se em `/mnt/beegfs/carlos.bastarz/SMNA_v3.0.x_check/anls_compare/pos/convert_to_netcdf/output/zarr`)
* Partes desse visualizador podem ser integrados ao SMNAMonitoringApp
* Partes do código desse repositório utilizam código gerado por IA

carlos.bastarz@inpe.br (19/03/2026)
