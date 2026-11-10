using Licamvel.App.ViewModels;

namespace Licamvel.App.Views;

public partial class LoginPage : ContentPage
{
    private readonly LoginViewModel _viewModel;

    // El ViewModel llega por inyección de dependencias (registrado en MauiProgram).
    public LoginPage(LoginViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        BindingContext = _viewModel;
    }

    protected override void OnAppearing()
    {
        base.OnAppearing();

        // Al volver a la pantalla (ej. tras cerrar sesión) se limpian credenciales y errores.
        _viewModel.Password = string.Empty;
        _viewModel.ErrorMessage = string.Empty;
    }
}